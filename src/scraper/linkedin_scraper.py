import asyncio
import random
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
        await page.click("button[type='submit']")
        
        # Espera carregar o feed para confirmar login
        try:
            await page.wait_for_selector(".global-nav__primary-link", timeout=10000)
            logger.info("Login realizado com sucesso.")
        except Exception:
            logger.error("Falha ao realizar login. Verifique as credenciais ou cheque por CAPTCHA.")
            raise Exception("Login Error")

    async def _scrape_jobs_for_query(self, context: BrowserContext, keyword: str, location: str, experiences: List[str]):
        page = await context.new_page()
        
        # Converte lista de niveis em parametro f_E
        exp_ids = [self.EXPERIENCE_MAP.get(e) for e in experiences if e in self.EXPERIENCE_MAP]
        exp_param = ",".join(exp_ids) if exp_ids else ""
        
        url = f"https://www.linkedin.com/jobs/search/?keywords={keyword}&location={location}"
        if exp_param:
            url += f"&f_E={exp_param}"
        
        logger.info(f"Buscando: '{keyword}' em '{location}' (Níveis: {experiences})")
        await page.goto(url)
        await asyncio.sleep(random.uniform(3, 5)) # Simula comportamento humano
        
        # Espera as vagas carregarem
        try:
            await page.wait_for_selector(".jobs-search-results-list", timeout=5000)
        except:
            logger.warning(f"Nenhuma vaga encontrada para '{keyword}' nesta combinação.")
            await page.close()
            return

        # Rola a lista para carregar mais itens
        for _ in range(3):
            await page.evaluate("document.querySelector('.jobs-search-results-list').scrollTop += 1000")
            await asyncio.sleep(1)

        # Extrai os cards das vagas
        job_cards = await page.query_selector_all(".job-card-container")
        for card in job_cards[:10]: # Limita a 10 por combinação para evitar bloqueios iniciais
            try:
                title_elem = await card.query_selector(".job-card-list__title")
                company_elem = await card.query_selector(".job-card-container__primary-description")
                link_elem = await card.query_selector("a.job-card-list__title")
                location_elem = await card.query_selector(".job-card-container__metadata-item")
                
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
            browser = await p.chromium.launch(headless=False) # Mude para False se quiser ver
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
