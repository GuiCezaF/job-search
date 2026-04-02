import asyncio
import random
import os
from datetime import datetime
from typing import List, Dict, Any
from playwright.async_api import async_playwright, Page, BrowserContext
from src.utils.logger import AppLogger

logger = AppLogger.setup_logger(__name__)

class LinkedInScraper:
    EXPERIENCE_MAP = {
        "Internship": "1",
        "Entry level": "2",
        "Associate": "3",
        "Mid-Senior level": "4",
        "Director": "5",
        "Executive": "6"
    }

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.results = []

    async def _login(self, page: Page):
        logger.info(f"Tentando login no LinkedIn para: {self.username}")
        await page.goto("https://www.linkedin.com/login")
        await page.fill("#username", self.username)
        await page.fill("#password", self.password)
        
        # Aguarda a página estabilizar
        await asyncio.sleep(2)
        
        try:
            checkbox_id = "#rememberMeOptIn-checkbox"
            label_selector = "label[for='rememberMeOptIn-checkbox']"
            
            is_checked = await page.is_checked(checkbox_id)
            logger.info(f"Estado inicial do 'Lembre-me': {'Marcado' if is_checked else 'Desmarcado'}")
            
            if is_checked:
                await page.click(label_selector, force=True)
                await asyncio.sleep(1)
                
                still_checked = await page.is_checked(checkbox_id)
                if not still_checked:
                    logger.info("Opção 'Mantenha-me conectado' desmarcada com sucesso.")
                else:
                    logger.warning("Tentativa de desmarcar falhou via clique, tentando via uncheck...")
                    await page.uncheck(checkbox_id, force=True)
            else:
                logger.info("Opção já estava desmarcada.")
        except Exception as e:
            logger.warning(f"Não foi possível interagir com o checkbox de login: {e}")

        await page.click("button[type='submit']")
        
        try:
            await page.wait_for_function(
                "() => window.location.href.includes('/feed/') || document.querySelector('.global-nav') !== null",
                timeout=15000
            )
            logger.info("Login realizado com sucesso.")
        except Exception:
            if "login" in page.url:
                logger.error("Falha ao realizar login. Verifique as credenciais ou cheque por CAPTCHA.")
                raise Exception("Login Error")
            else:
                logger.info("Login parece ter tido sucesso (URL alterada), prosseguindo...")

    async def _scrape_jobs_for_query(self, context: BrowserContext, keyword: str, location: str, experiences: List[str]):
        page = await context.new_page()
        
        exp_ids = [self.EXPERIENCE_MAP.get(e) for e in experiences if e in self.EXPERIENCE_MAP]
        exp_param = ",".join(exp_ids) if exp_ids else ""
        
        url = f"https://www.linkedin.com/jobs/search/?keywords={keyword}&location={location}"
        if exp_param:
            url += f"&f_E={exp_param}"
        
        logger.info(f"Buscando: '{keyword}' em '{location}' (Níveis: {experiences})")
        await page.goto(url)
        await asyncio.sleep(random.uniform(3, 5)) # Simula comportamento humano
        
        try:
            selectors = [
                ".scaffold-layout__list-container", 
                "ul.jobs-search-results__list", 
                ".jobs-search-results-list",
                "[data-view-name='job-card']",
                ".jobs-search-results-list__container"
            ]
            await page.wait_for_selector(", ".join(selectors), timeout=20000)
        except:
            no_jobs_msg = await page.query_selector(".jobs-search-two-pane__no-results-banner, .jobs-search-no-results-banner, .jobs-search-no-results")
            if no_jobs_msg:
                logger.warning(f"Nenhuma vaga encontrada para '{keyword}' nesta combinação.")
            else:
                logger.error(f"Erro ao detectar lista de vagas para '{keyword}'. Tentando extrair o que houver na tela mesmo assim...")
        
        list_container = await page.query_selector(".jobs-search-results-list, .scaffold-layout__list, [role='main'] ul")
        
        if list_container:
            logger.info("Fazendo scroll na lista de vagas...")
            for _ in range(6):
                # Move o mouse para cima da lista e rola
                box = await list_container.bounding_box()
                if box:
                    await page.mouse.move(box['x'] + 10, box['y'] + 10)
                    await page.mouse.wheel(0, 800)
                await asyncio.sleep(1)
        else:
            # Fallback se não achar o container específico
            await page.mouse.wheel(0, 2000)
            await asyncio.sleep(1)

        # Extrai os cards das vagas usando seletores mais abrangentes
        job_cards = await page.query_selector_all("[data-occludable-job-id], .job-card-container, .base-card, .jobs-search-results__list-item")
        
        logger.info(f"Cards detectados: {len(job_cards)}")
        
        for card in job_cards[:20]: 
            try:
                # Seletores para o Título e Empresa (tentando padrões diferentes)
                title_elem = await card.query_selector(".job-card-list__title, .job-card-container__link, h3, [data-view-name='job-card-title']")
                company_elem = await card.query_selector(".job-card-container__primary-description, .job-card-container__company-name, .base-search-card__subtitle, .job-card-container__secondary-subtitle")
                link_elem = await card.query_selector("a.job-card-list__title, a.job-card-container__link, a[href*='/jobs/view/']")
                location_elem = await card.query_selector(".job-card-container__metadata-item, .job-card-container__location, .job-card-container__metadata-wrapper")
                
                title = (await title_elem.inner_text()).strip() if title_elem else "N/A"
                company = (await company_elem.inner_text()).strip() if company_elem else "N/A"
                link = f"https://www.linkedin.com{await link_elem.get_attribute('href')}" if link_elem else "N/A"
                loc = (await location_elem.inner_text()).strip() if location_elem else location
                
                self.results.append({
                    "Título": title,
                    "Empresa": company,
                    "Local": loc,
                    "Link": link,
                    "Data de Busca": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Keyword": keyword,
                    "Filtro Experiência": ", ".join(experiences)
                })
            except Exception as e:
                logger.error(f"Erro ao extrair card: {e}")
        
        await page.close()

    async def run_scrape(self, keywords: List[str], locations: List[str], experiences: List[str]) -> List[Dict[str, Any]]:
        self.results = []
        async with async_playwright() as p:
            # No Docker, headless DEVE ser True. Localmente você pode mudar via .env
            headless = os.getenv("HEADLESS", "true").lower() == "true"
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()
            await self._login(page)
            
            for keyword in keywords:
                for location in locations:
                    await self._scrape_jobs_for_query(context, keyword, location, experiences)
                    await asyncio.sleep(random.uniform(2, 4))
            
            await browser.close()
            return self.results
