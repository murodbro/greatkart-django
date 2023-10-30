from .models import Category


def manu_link(request):
    links = Category.objects.all()
    return dict(links=links)