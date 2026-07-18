from apps.admin_panel.models import PlatformSetting
from apps.core.repositories.crud import CRUDRepository


class PlatformSettingRepository(CRUDRepository):
    model = PlatformSetting
