from django.shortcuts import render
import requests
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Profile
from .serializers import (
    ProfileFullSerializer,
    ProfileListSerializer,
    ProfileCreateSerializer,
)

# Create your views here.

def cors_headers(response):
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


def error_response(message, status_code):
    response = Response(
        {'status': 'error', 'message': message},
        status=status_code
    )
    return response


def get_age_group(age):
    if age <= 12:
        return 'child'
    elif age <= 19:
        return 'teenager'
    elif age <= 59:
        return 'adult'
    else:
        return 'senior'


def fetch_external_apis(name):
    """
    Calls Genderize, Agify, and Nationalize APIs.
    Returns (data_dict, error_response) — one will be None.
    """
    # Genderize
    try:
        g_resp = requests.get(
            'https://api.genderize.io', params={'name': name}, timeout=5
        )
        g_resp.raise_for_status()
        g_data = g_resp.json()
    except Exception:
        return None, 'Genderize returned an invalid response'

    gender = g_data.get('gender')
    gender_probability = g_data.get('probability')
    sample_size = g_data.get('count')

    if gender is None or sample_size == 0:
        return None, 'Genderize returned an invalid response'

    # Agify
    try:
        a_resp = requests.get(
            'https://api.agify.io', params={'name': name}, timeout=5
        )
        a_resp.raise_for_status()
        a_data = a_resp.json()
    except Exception:
        return None, 'Agify returned an invalid response'

    age = a_data.get('age')

    if age is None:
        return None, 'Agify returned an invalid response'

    # Nationalize
    try:
        n_resp = requests.get(
            'https://api.nationalize.io', params={'name': name}, timeout=5
        )
        n_resp.raise_for_status()
        n_data = n_resp.json()
    except Exception:
        return None, 'Nationalize returned an invalid response'

    countries = n_data.get('country', [])

    if not countries:
        return None, 'Nationalize returned an invalid response'

    top_country = max(countries, key=lambda c: c.get('probability', 0))
    country_id = top_country.get('country_id')
    country_probability = top_country.get('probability')

    return {
        'gender': gender,
        'gender_probability': gender_probability,
        'sample_size': sample_size,
        'age': age,
        'age_group': get_age_group(age),
        'country_id': country_id,
        'country_probability': country_probability,
    }, None


class HealthView(APIView):
    def get(self, request):
        response = Response({'status': 'ok'})
        return cors_headers(response)


class ProfileListView(APIView):

    def options(self, request, *args, **kwargs):
        response = Response(status=status.HTTP_200_OK)
        return cors_headers(response)

    def get(self, request):
        """GET /api/profiles/ — list all profiles with optional filters."""
        queryset = Profile.objects.all()

        gender = request.query_params.get('gender')
        country_id = request.query_params.get('country_id')
        age_group = request.query_params.get('age_group')

        if gender:
            queryset = queryset.filter(gender__iexact=gender)
        if country_id:
            queryset = queryset.filter(country_id__iexact=country_id)
        if age_group:
            queryset = queryset.filter(age_group__iexact=age_group)

        serializer = ProfileListSerializer(queryset, many=True)
        response = Response({
            'status': 'success',
            'count': queryset.count(),
            'data': serializer.data,
        }, status=status.HTTP_200_OK)
        return cors_headers(response)

    def post(self, request):
        """POST /api/profiles/ — create a new profile."""
        input_serializer = ProfileCreateSerializer(data=request.data)

        if not input_serializer.is_valid():
            response = error_response('Bad Request', status.HTTP_400_BAD_REQUEST)
            return cors_headers(response)

        name = input_serializer.validated_data['name']

        # Check if profile already exists (idempotency)
        existing = Profile.objects.filter(name=name).first()
        if existing:
            serializer = ProfileFullSerializer(existing)
            response = Response({
                'status': 'success',
                'message': 'Profile already exists',
                'data': serializer.data,
            }, status=status.HTTP_200_OK)
            return cors_headers(response)

        # Fetch external APIs
        api_data, api_error = fetch_external_apis(name)
        if api_error:
            response = error_response(api_error, status.HTTP_502_BAD_GATEWAY)
            return cors_headers(response)

        # Create profile
        profile = Profile.objects.create(name=name, **api_data)
        serializer = ProfileFullSerializer(profile)
        response = Response({
            'status': 'success',
            'data': serializer.data,
        }, status=status.HTTP_201_CREATED)
        return cors_headers(response)


class ProfileDetailView(APIView):

    def options(self, request, *args, **kwargs):
        response = Response(status=status.HTTP_200_OK)
        return cors_headers(response)

    def get_profile(self, profile_id):
        try:
            return Profile.objects.get(id=profile_id), None
        except (Profile.DoesNotExist, ValueError):
            return None, error_response('Profile not found', status.HTTP_404_NOT_FOUND)

    def get(self, request, profile_id):
        """GET /api/profiles/{id}/ — get single profile."""
        profile, err = self.get_profile(profile_id)
        if err:
            return cors_headers(err)

        serializer = ProfileFullSerializer(profile)
        response = Response({
            'status': 'success',
            'data': serializer.data,
        }, status=status.HTTP_200_OK)
        return cors_headers(response)

    def delete(self, request, profile_id):
        """DELETE /api/profiles/{id}/ — delete a profile."""
        profile, err = self.get_profile(profile_id)
        if err:
            return cors_headers(err)

        profile.delete()
        response = Response(status=status.HTTP_204_NO_CONTENT)
        return cors_headers(response)