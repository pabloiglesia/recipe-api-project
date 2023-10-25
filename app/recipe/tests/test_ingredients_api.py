"""
Test for the ingredients API
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse

from django.test import TestCase

from rest_framework import status

from rest_framework.test import APIClient
from core.models import (
    Ingredient,
    Recipe,
    RecipeIngredient
)

from recipe.serializers import IngredientSerializer


INGREDIENTS_URL = reverse('recipe:ingredient-list')


def detail_url(ingredient_id):
    """Create and return a ingredient detail url."""
    return reverse('recipe:ingredient-detail', args=[ingredient_id])


def create_user(email='user@exanple.con', password='testpass123'):
    """Create and return a user."""
    return get_user_model().objects.create_user(email=email, password=password)


class PublicIngredientsApiTests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required for retrieving ingredients."""
        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsApiTests(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients(self):
        """Test retrieving a list of ingredients."""
        Ingredient.objects.create(user=self.user, name='Vegan')
        Ingredient.objects.create(user=self.user, name='Dessert')

        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """Test list of ingredients is limited to authenticated user."""
        user2 = create_user(email='user2@example.com')
        Ingredient.objects.create(user=user2, name='Fruity')
        ingredient = Ingredient.objects.create(
            user=self.user,
            name='Comfort Food')
        ingredient.refresh_from_db()

        res = self.client.get(INGREDIENTS_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient.name)
        self.assertEqual(res.data[0]['id'], ingredient.id)

    def test_update_ingredient(self):
        """Test updating a ingredient."""

        ingredient = Ingredient.objects.create(
            user=self.user,
            name='After Dinner')
        payload = {'name': 'Dessert'}

        url = detail_url(ingredient.id)

        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload['name'].lower())

    def test_delete_ingredient(self):
        """Test deleting a ingredient."""

        ingredient = Ingredient.objects.create(
            user=self.user,
            name='Breakfast')

        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        ingredients = Ingredient.objects.filter(user=self.user)
        self.assertFalse(ingredients.exists())

    def test_filter_ingredients_assigned_to_recipes(self):
        """Test listing ingedients to those assigned to recipes."""
        in1 = Ingredient.objects.create(user=self.user, name='apples')
        in2 = Ingredient.objects.create(user=self.user, name='turkey')
        recipe_ingredient1 = RecipeIngredient.objects.create(
            ingredient=in1,
            quantity='1'
        )

        recipe = Recipe.objects.create(
            title='Apple Crumble',
            time_minutes=5,
            price=Decimal('4.50'),
            user=self.user,
        )
        recipe.ingredients.add(recipe_ingredient1)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        s1 = IngredientSerializer(in1)
        s2 = IngredientSerializer(in2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_ingredients_unique(self):
        """Test filtered ingredients returns a unique list."""
        ing = Ingredient.objects.create(user=self.user, name='Eggs')
        Ingredient.objects.create(user=self.user, name='Lentils')
        recipe_ingredient = RecipeIngredient.objects.create(
            ingredient=ing,
            quantity='1'
        )
        recipe1 = Recipe.objects.create(
            title='Eggs Benedict',
            time_minutes=60,
            price=Decimal('7.00'),
            user=self.user,
        )
        recipe2 = Recipe.objects.create(
            title='Herb Eggs',
            time_minutes=20,
            price=Decimal('4.00'),
            user=self.user,
        )
        recipe1.ingredients.add(recipe_ingredient)
        recipe2.ingredients.add(recipe_ingredient)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)

    def test_ingredients_not_case_sensitive(self):
        """Test that Ingrediente are not Case Sensitive."""
        Ingredient.objects.create(user=self.user, name='Eggs')
        Ingredient.objects.get_or_create(user=self.user, name='egGs')

        ingredients = Ingredient.objects.all()

        self.assertEqual(len(ingredients), 1)
