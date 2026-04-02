import asyncio
import os
import random
import re
from datetime import datetime
from typing import Any, Dict, List, Set

from playwright.async_api import (
    BrowserContext,
    ElementHandle,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

from src.types.exceptions import LoginError
from src.utils.logger import AppLogger

logger = AppLogger.setup_logger(__name__)


class LinkedInScraper:
    """
    Automação de busca de vagas no LinkedIn com Playwright (I/O assíncrono).

    Mantém estado em `results` apenas durante um ciclo de `run_scrape`.
    """

    EXPERIENCE_MAP = {
        "Internship": "1",
        "Entry level": "2",
        "Associate": "3",
        "Mid-Senior level": "4",
        "Director": "5",
        "Executive": "6",
    }

    # Limite de rodadas de scroll para carregar mais cards na lista virtualizada
    MAX_SCROLL_ROUNDS = 40

    def __init__(
        self,
        username: str,
        password: str,
        *,
        max_jobs_per_query: int = 32,
    ) -> None:
        """
        max_jobs_per_query: teto de vagas válidas por keyword+local (vem do YAML / SearchConfig).
        """
        if not username or not username.strip():
            raise ValueError("username não pode ser vazio")
        if not password:
            raise ValueError("password não pode ser vazio")
        if max_jobs_per_query < 1:
            raise ValueError("max_jobs_per_query deve ser >= 1")

        self.username = username.strip()
        self.password = password
        self.max_jobs_per_query = max_jobs_per_query
        self.results: List[Dict[str, Any]] = []

    async def _login(self, page: Page) -> None:
        logger.info(
            "Tentando login no LinkedIn",
            extra={"extra_fields": {"username": self.username}},
        )
        await page.goto("https://www.linkedin.com/login")
        await page.fill("#username", self.username)
        await page.fill("#password", self.password)

        await asyncio.sleep(2)

        try:
            checkbox_id = "#rememberMeOptIn-checkbox"
            label_selector = "label[for='rememberMeOptIn-checkbox']"

            is_checked = await page.is_checked(checkbox_id)
            logger.info(
                "Estado inicial do 'Lembre-me'",
                extra={"extra_fields": {"is_checked": is_checked}},
            )

            if is_checked:
                await page.click(label_selector, force=True)
                await asyncio.sleep(1)

                still_checked = await page.is_checked(checkbox_id)
                if not still_checked:
                    logger.info("Opção 'Mantenha-me conectado' desmarcada com sucesso.")
                else:
                    logger.warning(
                        "Tentativa de desmarcar falhou via clique; tentando uncheck"
                    )
                    await page.uncheck(checkbox_id, force=True)
            else:
                logger.info("Opção já estava desmarcada.")
        except Exception as err:
            logger.warning(
                "Não foi possível interagir com o checkbox de login",
                extra={"extra_fields": {"error": str(err)}},
            )

        await page.click("button[type='submit']")

        try:
            await page.wait_for_function(
                "() => window.location.href.includes('/feed/') || document.querySelector('.global-nav') !== null",
                timeout=15000,
            )
            logger.info("Login realizado com sucesso.")
        except PlaywrightTimeoutError:
            if "login" in page.url:
                logger.error(
                    "Falha ao realizar login",
                    extra={"extra_fields": {"url": page.url}},
                )
                raise LoginError(
                    "Verifique credenciais, CAPTCHA ou bloqueio da conta."
                )
            logger.info("Login parece ter tido sucesso (URL alterada), prosseguindo...")

    @staticmethod
    async def _should_skip_card(card: ElementHandle) -> bool:
        """
        Ignora anúncios patrocinados/promovidos e vagas já marcadas como visualizadas.

        Usa texto visível + classes comuns do layout atual do LinkedIn.
        """
        return await card.evaluate(
            """(el) => {
              const root = el.closest('[data-occludable-job-id]') || el;
              const text = (root.innerText || '').toLowerCase();
              const html = (root.innerHTML || '').toLowerCase();

              const promoted =
                /promoted|patrocinad[oa]|promovid[oa]/.test(text) ||
                html.includes('promoted') ||
                root.querySelector('[class*="promoted"]') !== null;

              const viewed =
                /\\bviewed\\b|\\bvisualizad[oa]\\b/.test(text) ||
                root.querySelector('[class*="viewed"]') !== null;

              return promoted || viewed;
            }"""
        )

    @staticmethod
    async def _job_id_from_card(card: ElementHandle) -> str:
        """Chave estável para deduplicar cards ao rolar a lista virtualizada."""
        attr = await card.get_attribute("data-occludable-job-id")
        if attr and attr.strip():
            return attr.strip()
        inner = await card.query_selector("[data-occludable-job-id]")
        if inner:
            inner_attr = await inner.get_attribute("data-occludable-job-id")
            if inner_attr and inner_attr.strip():
                return inner_attr.strip()
        href_el = await card.query_selector("a[href*='/jobs/view/']")
        if href_el:
            href = await href_el.get_attribute("href")
            if href:
                match = re.search(r"/jobs/view/(\d+)", href)
                if match:
                    return match.group(1)
        return ""

    async def _scroll_results_list(self, page: Page) -> bool:
        """
        Rola o painel lateral de resultados (overflow no container, não na página inteira).

        Retorna False se nenhum container rolável foi encontrado.
        """
        return await page.evaluate(
            """() => {
              const selectors = [
                '.scaffold-layout__list-container',
                '.jobs-search-results-list',
                '.scaffold-layout__list',
                '[class*="jobs-search-results-list"]',
                'div.jobs-search-results',
              ];
              for (const sel of selectors) {
                const el = document.querySelector(sel);
                if (!el) continue;
                const sh = el.scrollHeight;
                const ch = el.clientHeight;
                if (sh > ch + 20) {
                  const step = Math.min(900, sh - el.scrollTop - ch);
                  el.scrollBy(0, Math.max(400, step));
                  return true;
                }
              }
              return false;
            }"""
        )

    async def _scroll_last_job_into_view(self, page: Page) -> None:
        """Força o último card conhecido a entrar na viewport da lista (lazy load)."""
        handles = await page.query_selector_all("[data-occludable-job-id]")
        if not handles:
            return
        try:
            await handles[-1].scroll_into_view_if_needed()
        except Exception:
            pass

    @staticmethod
    def _normalize_job_url(href: str | None) -> str:
        if not href or href == "N/A":
            return "N/A"
        if href.startswith("http"):
            return href.split("?")[0]
        return f"https://www.linkedin.com{href.split('?')[0]}"

    async def _scrape_jobs_for_query(
        self,
        context: BrowserContext,
        keyword: str,
        location: str,
        experiences: List[str],
    ) -> None:
        page = await context.new_page()

        exp_ids = [self.EXPERIENCE_MAP[e] for e in experiences if e in self.EXPERIENCE_MAP]
        exp_param = ",".join(exp_ids) if exp_ids else ""

        url = f"https://www.linkedin.com/jobs/search/?keywords={keyword}&location={location}"
        if exp_param:
            url += f"&f_E={exp_param}"

        logger.info(
            "Buscando vagas",
            extra={
                "extra_fields": {
                    "keyword": keyword,
                    "location": location,
                    "experiences": experiences,
                }
            },
        )
        await page.goto(url)
        await asyncio.sleep(random.uniform(3, 5))

        selectors = [
            ".scaffold-layout__list-container",
            "ul.jobs-search-results__list",
            ".jobs-search-results-list",
            "[data-view-name='job-card']",
            ".jobs-search-results-list__container",
        ]
        try:
            await page.wait_for_selector(", ".join(selectors), timeout=20000)
        except PlaywrightTimeoutError:
            no_jobs_msg = await page.query_selector(
                ".jobs-search-two-pane__no-results-banner, .jobs-search-no-results-banner, .jobs-search-no-results"
            )
            if no_jobs_msg:
                logger.warning(
                    "Nenhuma vaga encontrada para esta combinação",
                    extra={"extra_fields": {"keyword": keyword, "location": location}},
                )
            else:
                logger.error(
                    "Timeout ao detectar lista de vagas; tentando extrair o que houver",
                    extra={"extra_fields": {"keyword": keyword, "location": location}},
                )
        except Exception as err:
            logger.error(
                "Erro ao aguardar lista de vagas",
                extra={"extra_fields": {"keyword": keyword, "error": str(err)}},
            )

        seen_job_ids: Set[str] = set()
        collected = 0
        stagnant_rounds = 0

        card_selector = "[data-occludable-job-id]"

        for round_idx in range(self.MAX_SCROLL_ROUNDS):
            if collected >= self.max_jobs_per_query:
                break

            job_cards = await page.query_selector_all(card_selector)
            seen_size_before = len(seen_job_ids)

            for card in job_cards:
                if collected >= self.max_jobs_per_query:
                    break

                job_id = await self._job_id_from_card(card)
                dedup_key = job_id or await card.evaluate("el => el.outerHTML.slice(0, 200)")
                if dedup_key in seen_job_ids:
                    continue
                seen_job_ids.add(dedup_key)

                if await self._should_skip_card(card):
                    continue

                try:
                    title_elem = await card.query_selector(
                        ".job-card-list__title, .job-card-container__link, h3, [data-view-name='job-card-title']"
                    )
                    company_elem = await card.query_selector(
                        ".job-card-container__primary-description, .job-card-container__company-name, .base-search-card__subtitle, .job-card-container__secondary-subtitle"
                    )
                    link_elem = await card.query_selector(
                        "a.job-card-list__title, a.job-card-container__link, a[href*='/jobs/view/']"
                    )
                    location_elem = await card.query_selector(
                        ".job-card-container__metadata-item, .job-card-container__location, .job-card-container__metadata-wrapper"
                    )

                    title = (await title_elem.inner_text()).strip() if title_elem else "N/A"
                    company = (await company_elem.inner_text()).strip() if company_elem else "N/A"
                    raw_href = await link_elem.get_attribute("href") if link_elem else None
                    link = self._normalize_job_url(raw_href)
                    loc = (await location_elem.inner_text()).strip() if location_elem else location

                    self.results.append(
                        {
                            "Título": title,
                            "Empresa": company,
                            "Local": loc,
                            "Link": link,
                            "Data de Busca": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Keyword": keyword,
                            "Filtro Experiência": ", ".join(experiences),
                        }
                    )
                    collected += 1
                except Exception as err:
                    logger.error(
                        "Erro ao extrair card",
                        extra={
                            "extra_fields": {
                                "keyword": keyword,
                                "error": str(err),
                            }
                        },
                    )

            if collected >= self.max_jobs_per_query:
                break

            new_ids_this_round = len(seen_job_ids) - seen_size_before
            if new_ids_this_round == 0 and round_idx > 0:
                stagnant_rounds += 1
            else:
                stagnant_rounds = 0

            scrolled = await self._scroll_results_list(page)
            await self._scroll_last_job_into_view(page)
            if not scrolled:
                await page.mouse.wheel(0, 600)

            await asyncio.sleep(random.uniform(0.7, 1.3))

            if stagnant_rounds >= 5:
                logger.info(
                    "Scroll sem novos job ids; encerrando coleta desta busca",
                    extra={
                        "extra_fields": {
                            "keyword": keyword,
                            "collected": collected,
                            "round": round_idx,
                        }
                    },
                )
                break

        logger.info(
            "Vagas coletadas para a busca",
            extra={
                "extra_fields": {
                    "keyword": keyword,
                    "location": location,
                    "aceitas": collected,
                    "max": self.max_jobs_per_query,
                }
            },
        )

        await page.close()

    async def run_scrape(
        self,
        keywords: List[str],
        locations: List[str],
        experiences: List[str],
    ) -> List[Dict[str, Any]]:
        if not keywords:
            logger.warning("Lista de keywords vazia; nada a buscar.")
            return []

        self.results = []
        async with async_playwright() as playwright:
            headless = os.getenv("HEADLESS", "true").lower() == "true"
            browser = await playwright.chromium.launch(headless=headless)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                )
            )

            page = await context.new_page()
            await self._login(page)

            for keyword in keywords:
                for location in locations:
                    await self._scrape_jobs_for_query(context, keyword, location, experiences)
                    await asyncio.sleep(random.uniform(2, 4))

            await browser.close()

        return self.results
