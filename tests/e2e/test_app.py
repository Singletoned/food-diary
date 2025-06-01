    def test_homepage_has_title(self):
        """Test that the homepage loads and contains the expected title"""
        self.page.goto(BASE_URL)
        title_element = self.page.get_by_role("heading", name="Food Diary Entry")
        assert title_element.is_visible(), "Expected title 'Food Diary Entry' not found on page"

