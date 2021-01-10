from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient
from recipe.serializers import RecipeSerializer, RecipeDetailSerializer


RECIPIES_URL = reverse('recipe:recipe-list')

# api/recipe/recipes/1


def detail_url(recipe_id):
    """Return recipe detail url"""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def sample_tag(user, name='Test course'):
    """Create and return sample recipe tag"""
    return Tag.objects.create(user=user, name=name)


def sample_ingredient(user, name='Test Tomato'):
    """Create and return sample recipe ingredient"""
    return Ingredient.objects.create(user=user, name=name)


def sample_recipe(user, **params):
    """Create and return a sample recipe"""
    defaults = {
        'title': 'Sample recipe',
        'time_minutes': 10,
        'price': 5.00
    }
    defaults.update(params)
    return Recipe.objects.create(user=user, **defaults)


class PublicRecipeApiTests(TestCase):
    """Test unauthentificated recipe API"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentificated is required"""
        res = self.client.get(RECIPIES_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTest(TestCase):
    """Test authentificated recipe access"""

    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            email='test@developer.de',
            password='test_password'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrive_recipes(self):
        """Test retrive recipes for authentificated user"""
        sample_recipe(self.user)
        sample_recipe(self.user)

        res = self.client.get(RECIPIES_URL)

        recipies = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipes_limited_to_user(self):
        """Test recipies limited to user"""
        user2 = get_user_model().objects.create_user(
            email='testuser2@developer.de',
            password='testpass2'
        )
        sample_recipe(user=self.user)
        sample_recipe(user=user2)

        res = self.client.get(RECIPIES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data, serializer.data)

    def test_view_recipe_detail(self):
        """Test viewing recipe detail"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        recipe.ingredients.add(sample_ingredient(user=self.user))

        url = detail_url(recipe.id)

        res = self.client.get(url)
        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)

    def test_create_basic_recipe(self):
        """Test creating recipe"""
        payload = {
            'title': 'Chocolate cheesecake',
            'time_minutes': 30,
            'price': 5.00
        }
        res = self.client.post(RECIPIES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(recipe, key))

    def create_recipe_with_tags(self):
        """Test creating recipe with tags"""
        tag1 = sample_tag(self.user, name='Vegan')
        tag2 = sample_tag(self.user, name='Dessert')
        payload = {
            'title': 'Avocado lime cheesecake',
            'time_minutes': 25,
            'price': 20.00,
            'tags': [tag1.id, tag2.id],
        }
        res = self.client.post(RECIPIES_URL, payload)
        self.assertTrue(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        tags = recipe.tags.all()
        self.assertEqual(tags.count(), 2)
        self.assertIn(tag1, tags)
        self.assertIn(tag2, tags)

    def test_create_recipe_with_ingredients(self):
        """Test create recipe with ingredients"""
        ingredient1 = sample_ingredient(user=self.user, name='Prawns')
        ingredient2 = sample_ingredient(user=self.user, name='Ginger')

        payload = {
            'title': 'Thai prawn red curry',
            'price': 15.00,
            'time_minutes': 25,
            'ingredients': [ingredient1.id, ingredient2.id],
        }

        res = self.client.post(RECIPIES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        ingredients = recipe.ingredients.all()
        self.assertEqual(ingredients.count(), 2)
        self.assertIn(ingredient1, ingredients)
        self.assertIn(ingredient2, ingredients)

    def test_partial_update_recipe(self):
        """Test updating a recipe with patch"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))

        new_tag = sample_tag(user=self.user, name='Curry')
        payload = {
            'title': 'Chicken tikka',
            'tags': [new_tag.id]
        }
        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        tags = recipe.tags.all()
        self.assertEqual(len(tags), 1)
        self.assertIn(new_tag, tags)

    def test_full_update_recipe(self):
        """Test updating recipe with put"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        payload = {
            'title': 'Spagetti carbonara',
            'time_minutes': 20,
            'price': 10
        }
        url = detail_url(recipe.id)
        self.client.put(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.time_minutes, payload['time_minutes'])
        self.assertEqual(recipe.price, payload['price'])
        tags = recipe.tags.all()
        self.assertEqual(tags.count(), 0)
