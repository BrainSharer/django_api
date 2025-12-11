from rest_framework.pagination import LimitOffsetPagination
from rest_framework.pagination import PageNumberPagination

class DataTablePagination(LimitOffsetPagination):
        limit_query_param = 'lengthXXX'
        offset_query_param = 'startYYY'

class LargeResultsSetPagination(LimitOffsetPagination):
        page_size = 100


class SlidePagination(PageNumberPagination):
        page_size = 150  # Set your desired page size here
        page_size_query_param = 'limit' # Optional: Allows client to override page size
        max_page_size = 200 # Optional: Sets an upper limit for client-requested page size