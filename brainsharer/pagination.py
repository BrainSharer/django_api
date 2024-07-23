from rest_framework.pagination import LimitOffsetPagination

class DataTablePagination(LimitOffsetPagination):
        limit_query_param = 'lengthXXX'
        offset_query_param = 'startYYY'

class LargeResultsSetPagination(LimitOffsetPagination):
        page_size = 100
