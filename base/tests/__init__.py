class MyTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # runs ONCE for the whole class — use for read-only data
        cls.session = Session.objects.create(...)

    def setUp(self):
        # runs before EVERY test method — use for data that changes
        self.account = StudentFeeAccount.objects.create(...)
