from django.views import View
from django.shortcuts import render


class ErrorNotFound(View):
    def get(self, request, resource):
        context = {
            'failed_url': resource
        }

        print(context)
        return render(request, 'base/error-404.html', context)
