"""
Tests simples pour l'API d'exportation des Items en Excel et CSV

Test de l'API : /items/all_items/?draw=1&start=0&length=20&search[value]=&search[regex]=false
Utilisateur requis : ettahri@gmail.com / user1234
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status


class ItemExportSimpleTestCase(TestCase):
    """
    Tests simples de l'API d'exportation des items
    """
    
    def setUp(self):
        """Configuration initiale"""
        self.client = APIClient()
        
        # S'authentifier avec l'utilisateur existant
        token_response = self.client.post('/api/token/', {
            'email': 'ettahri@gmail.com',
            'password': 'user1234'
        })
        
        if token_response.status_code == 200:
            access_token = token_response.data.get('access')
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
            print(f"✓ Authentification réussie")
        else:
            self.fail("Échec de l'authentification. Vérifiez que l'utilisateur ettahri@gmail.com existe avec le mot de passe user1234")
    
    def test_export_items_excel(self):
        """Test simple d'export Excel"""
        # Paramètres de l'API
        url = '/items/all_items/'
        params = {
            'draw': 1,
            'start': 0,
            'length': 20,
            'search[value]': '',
            'search[regex]': 'false',
            'export': 'excel'
        }
        
        # Appeler l'API
        response = self.client.get(url, params)
        
        # Vérifications
        self.assertEqual(response.status_code, status.HTTP_200_OK, 
                        f"Statut attendu: 200, reçu: {response.status_code}")
        
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            "Le type de contenu devrait être Excel"
        )
        
        self.assertIn('attachment', response.get('Content-Disposition', ''),
                     "Content-Disposition devrait contenir 'attachment'")
        
        print(f"✓ Export Excel réussi - Taille du fichier: {len(response.content)} octets")
    
    def test_export_items_csv(self):
        """Test simple d'export CSV"""
        # Paramètres de l'API
        url = '/items/all_items/'
        params = {
            'draw': 1,
            'start': 0,
            'length': 20,
            'search[value]': '',
            'search[regex]': 'false',
            'export': 'csv'
        }
        
        # Appeler l'API
        response = self.client.get(url, params)
        
        # Vérifications
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                        f"Statut attendu: 200, reçu: {response.status_code}")
        
        self.assertIn('text/csv', response['Content-Type'],
                     "Le type de contenu devrait être CSV")
        
        self.assertIn('attachment', response.get('Content-Disposition', ''),
                     "Content-Disposition devrait contenir 'attachment'")
        
        print(f"✓ Export CSV réussi - Taille du fichier: {len(response.content)} octets")
    
    def test_api_without_export(self):
        """Test de l'API sans export (retour JSON normal)"""
        # Paramètres de l'API sans export
        url = '/items/all_items/'
        params = {
            'draw': 1,
            'start': 0,
            'length': 20,
            'search[value]': '',
            'search[regex]': 'false'
        }
        
        # Appeler l'API
        response = self.client.get(url, params)
        
        # Vérifications
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Vérifier que c'est du JSON
        self.assertIn('application/json', response['Content-Type'])
        
        # Vérifier la structure DataTable
        data = response.json()
        self.assertIn('draw', data, "La réponse devrait contenir 'draw'")
        self.assertIn('recordsTotal', data, "La réponse devrait contenir 'recordsTotal'")
        self.assertIn('recordsFiltered', data, "La réponse devrait contenir 'recordsFiltered'")
        self.assertIn('data', data, "La réponse devrait contenir 'data'")
        
        print(f"✓ API DataTable réussie - {data['recordsTotal']} items totaux, {data['recordsFiltered']} filtrés")
    
    def test_export_without_authentication(self):
        """Test d'export sans authentification"""
        # Créer un nouveau client non authentifié
        client_non_auth = APIClient()
        
        url = '/items/all_items/'
        params = {
            'draw': 1,
            'start': 0,
            'length': 20,
            'export': 'excel'
        }
        
        # Appeler l'API sans authentification
        response = client_non_auth.get(url, params)
        
        # Devrait être refusé
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED,
                        "L'accès devrait être refusé sans authentification")
        
        print("✓ Accès refusé sans authentification (401)")
    
    def test_export_items_excel_exact_endpoint(self):
        """Test d'export Excel avec l'endpoint exact spécifié"""
        # Endpoint exact comme spécifié
        url = '/items/all_items/'
        params = {
            'draw': '1',
            'start': '0',
            'length': '20',
            'search[value]': '',
            'search[regex]': 'false',
            'export': 'excel'
        }
        
        response = self.client.get(url, params)
        
        # Vérifications
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                        f"Statut attendu: 200, reçu: {response.status_code}")
        
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            "Le type de contenu devrait être Excel"
        )
        
        self.assertIn('attachment', response.get('Content-Disposition', ''),
                     "Content-Disposition devrait contenir 'attachment'")
        
        print(f"✓ Export Excel endpoint exact réussi - Taille: {len(response.content)} octets")
        print(f"✓ URL testée: {url}?draw=1&start=0&length=20&search[value]=&search[regex]=false&export=excel")
    
    def test_export_items_csv_exact_endpoint(self):
        """Test d'export CSV avec l'endpoint exact spécifié"""
        # Endpoint exact comme spécifié
        url = '/items/all_items/'
        params = {
            'draw': '1',
            'start': '0',
            'length': '20',
            'search[value]': '',
            'search[regex]': 'false',
            'export': 'csv'
        }
        
        response = self.client.get(url, params)
        
        # Vérifications
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                        f"Statut attendu: 200, reçu: {response.status_code}")
        
        self.assertIn('text/csv', response['Content-Type'],
                     "Le type de contenu devrait être CSV")
        
        self.assertIn('attachment', response.get('Content-Disposition', ''),
                     "Content-Disposition devrait contenir 'attachment'")
        
        print(f"✓ Export CSV endpoint exact réussi - Taille: {len(response.content)} octets")
        print(f"✓ URL testée: {url}?draw=1&start=0&length=20&search[value]=&search[regex]=false&export=csv")
    
    def test_export_items_excel_with_fournisseur_filter(self):
        """Test d'export Excel avec filtre fournisseur (fournisseur_exact=REPER)"""
        url = '/items/all_items/'
        params = {
            'export': 'excel',
            'fournisseur_exact': 'REPER'
        }
        
        response = self.client.get(url, params)
        
        # Vérifications
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                        f"Statut attendu: 200, reçu: {response.status_code}")
        
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            "Le type de contenu devrait être Excel"
        )
        
        self.assertIn('attachment', response.get('Content-Disposition', ''),
                     "Content-Disposition devrait contenir 'attachment'")
        
        print(f"✓ Export Excel avec filtre fournisseur=REPER réussi")
        print(f"✓ Taille: {len(response.content)} octets")
        print(f"✓ URL testée: {url}?export=excel&fournisseur_exact=REPER")
    
    def test_export_items_csv_with_fournisseur_filter(self):
        """Test d'export CSV avec filtre fournisseur (fournisseur_exact=REPER)"""
        url = '/items/all_items/'
        params = {
            'export': 'csv',
            'fournisseur_exact': 'REPER'
        }
        
        response = self.client.get(url, params)
        
        # Vérifications
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                        f"Statut attendu: 200, reçu: {response.status_code}")
        
        self.assertIn('text/csv', response['Content-Type'],
                     "Le type de contenu devrait être CSV")
        
        self.assertIn('attachment', response.get('Content-Disposition', ''),
                     "Content-Disposition devrait contenir 'attachment'")
        
        print(f"✓ Export CSV avec filtre fournisseur=REPER réussi")
        print(f"✓ Taille: {len(response.content)} octets")
        print(f"✓ URL testée: {url}?export=csv&fournisseur_exact=REPER")


# =============================================================================
# EXÉCUTION DES TESTS
# =============================================================================

if __name__ == '__main__':
    import unittest
    unittest.main()
