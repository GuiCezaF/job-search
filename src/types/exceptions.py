class AppError(Exception):
    """Exceção base da aplicação para mapear falhas em mensagens amigáveis na CLI."""


class ConfigError(AppError):
    """Configuração ausente, ilegível ou inválida após validação Pydantic."""


class ScannerError(AppError):
    """Falha genérica em etapas de coleta automatizada (scraping)."""


class LoginError(ScannerError):
    """Autenticação no LinkedIn não concluiu dentro do tempo ou URL indicou falha."""


class SearchError(ScannerError):
    """Busca ou parse da listagem de vagas falhou (uso opcional pelos scrapers)."""


class ReportingError(AppError):
    """Falha ao persistir resultados ou enviar notificações externas."""
