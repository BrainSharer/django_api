from django.contrib.admin import SimpleListFilter
class UrlFilter(SimpleListFilter):
    """
    This filter is being used in django admin panel in profile model.
    """
    title = 'Url Types'
    parameter_name = 'comments'

    def lookups(self, request, model_admin):
        return (
            ('plain', 'Plain'),
            ('com annotation', 'Com Annotation'),
            ('cell detection', 'Cell Detection'),
            ('others','Others')
        )

    def queryset(self, request, queryset):
        if not self.value():
            return queryset
        if self.value().lower() == 'plain':
            return queryset.filter(comments__endswith = 'plain' )
        if self.value().lower() == 'cell detection':
            return queryset.filter(comments__icontains = 'cell detection' )
        if self.value().lower() == 'com annotation':
            return queryset.filter(comments__icontains = 'com annotation' )
        elif self.value().lower() == 'others':
            return queryset.filter().exclude(comments__icontains = 'plain')\
                .exclude(comments__icontains = 'cell detection')\
                .exclude(comments__icontains = 'com annotation')