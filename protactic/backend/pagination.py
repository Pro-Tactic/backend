from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ClubePagination(DefaultPagination):
    page_size = 30


class JogadorPagination(DefaultPagination):
    page_size = 25


class PartidaPagination(DefaultPagination):
    page_size = 15
