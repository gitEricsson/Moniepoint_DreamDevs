from src.modules.analytics.schemas.analytics import (
    FailureRateItem,
    KYCFunnelResponse,
    TopMerchantResponse,
)
from src.modules.analytics.services.analytics_service import AnalyticsService

class AnalyticsController:
    def __init__(self, service: AnalyticsService) -> None:
        self.service = service

    async def top_merchant(self) -> TopMerchantResponse:
        return await self.service.get_top_merchant()

    async def monthly_active_merchants(self) -> dict[str, int]:
        return await self.service.get_monthly_active_merchants()

    async def product_adoption(self) -> dict[str, int]:
        return await self.service.get_product_adoption()

    async def kyc_funnel(self) -> KYCFunnelResponse:
        return await self.service.get_kyc_funnel()

    async def failure_rates(self) -> list[FailureRateItem]:
        return await self.service.get_failure_rates()
