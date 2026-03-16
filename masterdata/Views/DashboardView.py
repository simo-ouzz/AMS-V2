from datetime import datetime
from decimal import Decimal
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework import status

from rest_framework.generics import ListAPIView
from django.db.models import Count,Sum
from django.db.models import F,Q
from masterdata.models import Personne, article, categorie, item, location, tag, type_tag,departement
from masterdata.serializers import (
    AmortizationCountSerializer,
    ArchivedItemsCountSerializer,
    ArticleCountSerializer,
    CategorieItemCountSerializer,
    DepartementCountSerializer,
    DepartementSerializer,
    FinancialValueSerializer,
    ItemCountSerializer,
    LocationWithEmplacementCountSerializer,
    PersonneItemSummarySerializer,
    TypeTagCountSerializer,
    tagsCountSerializer,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class CategorieItemCountView(ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = categorie.objects.annotate(total_items=Count("produit__article__item"))
    serializer_class = CategorieItemCountSerializer


class TypeTagCountCountView(ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = type_tag.objects.annotate(total_items=Count('tag', filter=Q(tag__affecter=False)))
    serializer_class = TypeTagCountSerializer


class ItemsCountCountView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ItemCountSerializer

    def get_queryset(self):
        return item.objects.filter(archive=False).count()

    def get(self, request, *args, **kwargs):
        count = self.get_queryset()
        serializer = self.get_serializer({"count": count})
        return Response(serializer.data)


class ArticleCountView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ArticleCountSerializer

    def get_queryset(self):
        return article.objects.filter(qte=F("qte_recue")).count()

    def get(self, request, *args, **kwargs):
        count = self.get_queryset()
        serializer = self.get_serializer({"count": count})
        return Response(serializer.data)


class TagsCountCountView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = tagsCountSerializer

    def get_queryset(self):
        return tag.objects.filter(affecter= False).count()

    def get(self, request, *args, **kwargs):
        count = self.get_queryset()
        print(count)
        serializer = self.get_serializer({"count": count})
        return Response(serializer.data)


class ArchivedItemsCountView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ArchivedItemsCountSerializer

    def get_queryset(self):

        return item.objects.filter(archive=True).count()

    def get(self, request, *args, **kwargs):
        count = self.get_queryset()
        serializer = self.get_serializer({"count": count})
        return Response(serializer.data)


class AmortizationCountView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AmortizationCountSerializer

    def get(self, request, year):
        if year is None:
            return Response({"error": "Year parameter is required."}, status=400)

        try:
            year = int(year)
        except ValueError:
            return Response({"error": "Year parameter must be an integer."}, status=400)

        # Récupération des items pour l'année spécifiée
        items_for_year = item.objects.filter(date_affectation__year=year)

        # Initialiser les totaux
        total_amortized = 0
        total_non_amortized = 0

        # Calculer la valeur résiduelle pour chaque item et compter
        for item_instance in items_for_year:
            residual_value = item_instance.calculate_residual_value()
            if residual_value == 0:
                total_amortized += 1
            elif residual_value > 0:
                total_non_amortized += 1

        data = {
            "total_amortized": total_amortized,
            "total_non_amortized": total_non_amortized,
        }

        return Response(data)
    
class ResidualValueGlobalCurrentYearView(ListAPIView):
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        current_year = datetime.now().year

        # Filtrer les items archivés pour l'année en cours
        archived_items = item.objects.filter(archive=True, date_archive__year=current_year)

        total_residual_value = 0

        # Calculer la somme des valeurs résiduelles
        for archived_item in archived_items:
            residual_value = archived_item.calculate_residual_value()
            if residual_value is not None:
                total_residual_value += residual_value

        # Retourner la réponse
        return Response({
            'total_residual_value': total_residual_value
        })




class FinancialValueByDepartmentView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FinancialValueSerializer

    def get_queryset(self):
        year = self.kwargs['year']
        compte = self.request.user.compte
        # Validate the year range
        if year < 1900 or year > timezone.now().year:
            raise ValueError("Invalid year provided.")

        # Get all departments
        departments = departement.objects.filter(compte=compte)
        results = {}

        # Iterate through each department
        for department in departments:
            # Get all non-archived items related to the current department
            items = item.objects.filter(departement=department, archive=False, article__date_achat__year=year,article__compte=compte)

            # Calculate total residual value for the department
            total_residual_value = Decimal(0)  # Initialize as 0

            for itm in items:
                residual_value = itm.calculate_residual_value(year)
                total_residual_value += Decimal(residual_value)

            # Store the result for the department
            results[department.nom] = total_residual_value

        # Convert results into a format suitable for the serializer
        data_to_serialize = [{'name': name, 'value': value} for name, value in results.items()]

        # Log the data to ensure it has the correct structure
        print(data_to_serialize)

        return data_to_serialize  # Return data ready for serialization

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class LocationListAPIView(ListAPIView):
    serializer_class = LocationWithEmplacementCountSerializer

    def get_queryset(self):
        return location.objects.annotate(value=Count('zone__emplacement'))



class DepartementListView(ListAPIView):
    serializer_class = DepartementCountSerializer
    permission_classes = [IsAuthenticated]  # Exiger que l'utilisateur soit authentifié

    def get_queryset(self):
        compte = self.request.user.compte
        return departement.objects.filter(compte=compte)

class PersonneItemSummaryListView(ListAPIView):
    serializer_class = PersonneItemSummarySerializer

    def get_queryset(self):
        # Filtrer les personnes par les comptes associés à l'utilisateur connecté
        compte = self.request.user.compte  # Assurez-vous que l'utilisateur a un compte
        return Personne.objects.filter(compte=compte) 
    
    
class GlobalResidualValueAPIView(APIView):
    def get(self, request):
        compte = request.user.compte
        items = item.objects.filter(article__compte=compte) 
        total_residual_value = sum(
            [itm.calculate_residual_value() for itm in items if itm.calculate_residual_value() is not None]
        )
        return Response({"valeur_residuelle_globale": total_residual_value}, status=status.HTTP_200_OK)
    
class ResidualValueByCategoryAPIView(APIView):
    def get(self, request):
        compte = request.user.compte
        categories = categorie.objects.all()
        result = {}
        for cat in categories:
            total_by_category = sum(
                [
                    itm.calculate_residual_value()
                    for itm in item.objects.filter(article__produit__categorie=cat,article__compte=compte)
                    if itm.calculate_residual_value() is not None
                ]
            )
            result[cat.libelle] = total_by_category

        return Response({"valeur_residuelle_par_categorie": result}, status=status.HTTP_200_OK)
