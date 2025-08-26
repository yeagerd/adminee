"""
Tests for AliasChoices class.
"""


from services.api.v1.common.models.base import AliasChoices


class TestAliasChoices:
    """Test AliasChoices functionality."""

    def test_alias_choices_creation(self):
        """Test creating AliasChoices with various choices."""
        choices = AliasChoices("choice1", "choice2", "choice3")
        assert choices.choices == ["choice1", "choice2", "choice3"]

    def test_alias_choices_iteration(self):
        """Test that AliasChoices can be iterated over."""
        choices = AliasChoices("choice1", "choice2", "choice3")

        # Should be iterable
        assert hasattr(choices, "__iter__")

        # Should iterate over the choices
        iterated_choices = list(choices)
        assert iterated_choices == ["choice1", "choice2", "choice3"]

    def test_alias_choices_multiple_iterations(self):
        """Test that AliasChoices can be iterated over multiple times."""
        choices = AliasChoices("choice1", "choice2", "choice3")

        # First iteration
        first_iteration = list(choices)
        assert first_iteration == ["choice1", "choice2", "choice3"]

        # Second iteration (should work the same)
        second_iteration = list(choices)
        assert second_iteration == ["choice1", "choice2", "choice3"]

    def test_alias_choices_empty(self):
        """Test AliasChoices with no choices."""
        choices = AliasChoices()
        assert choices.choices == []

        # Should iterate over empty list
        iterated_choices = list(choices)
        assert iterated_choices == []

    def test_alias_choices_single_choice(self):
        """Test AliasChoices with a single choice."""
        choices = AliasChoices("single_choice")
        assert choices.choices == ["single_choice"]

        # Should iterate over single choice
        iterated_choices = list(choices)
        assert iterated_choices == ["single_choice"]

    def test_alias_choices_in_for_loop(self):
        """Test AliasChoices in a for loop."""
        choices = AliasChoices("choice1", "choice2", "choice3")

        collected = []
        for choice in choices:
            collected.append(choice)

        assert collected == ["choice1", "choice2", "choice3"]

    def test_alias_choices_list_comprehension(self):
        """Test AliasChoices in list comprehension."""
        choices = AliasChoices("choice1", "choice2", "choice3")

        # Should work in list comprehension
        upper_choices = [choice.upper() for choice in choices]
        assert upper_choices == ["CHOICE1", "CHOICE2", "CHOICE3"]

    def test_alias_choices_is_not_iterator(self):
        """Test that AliasChoices itself is not an iterator."""
        choices = AliasChoices("choice1", "choice2", "choice3")

        # AliasChoices should be iterable but not an iterator
        assert hasattr(choices, "__iter__")
        assert not hasattr(choices, "__next__")

        # The __iter__ method should return a new iterator each time
        iterator1 = iter(choices)
        iterator2 = iter(choices)
        assert iterator1 is not iterator2
