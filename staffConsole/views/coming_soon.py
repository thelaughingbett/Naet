from django.shortcuts import render
from django.views import View


class ComingSoonView(View):
    def get(self, request):
        return render(request, 'staffConsole/coming-soon.html')
