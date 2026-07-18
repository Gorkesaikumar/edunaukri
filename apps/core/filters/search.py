from rest_framework.filters import SearchFilter

from apps.core.constants.app_constants import DEFAULT_SEARCH_PARAM


class StandardSearchFilter(SearchFilter):
    search_param = DEFAULT_SEARCH_PARAM
