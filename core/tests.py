from django.test import TestCase


class PageTests(TestCase):
    def test_index_renders_ava_interface(self):
        response = self.client.get("/")
        self.assertContains(response, "Live camera")
        self.assertContains(response, "SCAN")
