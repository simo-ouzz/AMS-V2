// custom_admin.js
document.addEventListener('DOMContentLoaded', function () {
    // Sélectionnez tous les liens de la barre latérale
    const sidebarLinks = document.querySelectorAll('.nav-sidebar .nav-link');

    // Ajoutez des attributs pour les tooltips Bootstrap
    sidebarLinks.forEach(link => {
        switch (link.getAttribute('href')) {
            case '/admin/masterdata/userweb/':
                link.setAttribute('data-bs-toggle', 'tooltip');
                link.setAttribute('data-bs-placement', 'right'); // Positionnez le tooltip comme nécessaire
                link.setAttribute('data-bs-title', 'Gérer les utilisateurs');
                break;
            case '/admin/masterdata/categorie/':
                link.setAttribute('data-bs-toggle', 'tooltip');
                link.setAttribute('data-bs-placement', 'right');
                link.setAttribute('data-bs-title', 'Gérer les catégories');
                break;
            case '/admin/masterdata/produit/':
                link.setAttribute('data-bs-toggle', 'tooltip');
                link.setAttribute('data-bs-placement', 'right');
                link.setAttribute('data-bs-title', 'Gérer les familles');
                break;
            // Ajoutez des cas pour d'autres liens selon vos besoins
            case '/admin/masterdata/nature/':
                link.setAttribute('data-bs-toggle', 'tooltip');
                link.setAttribute('data-bs-placement', 'right');
                link.setAttribute('data-bs-title', 'Gérer les natures');
                break;
            case '/admin/masterdata/marque/':
                link.setAttribute('data-bs-toggle', 'tooltip');
                link.setAttribute('data-bs-placement', 'right');
                link.setAttribute('data-bs-title', 'Gérer les marques');
                break;
            case '/admin/masterdata/fournisseur/':
            link.setAttribute('data-bs-toggle', 'tooltip');
            link.setAttribute('data-bs-placement', 'right');
            link.setAttribute('data-bs-title', 'Gérer les fournisseurs');
            break;
            case '/admin/masterdata/zone/':
            link.setAttribute('data-bs-toggle', 'tooltip');
            link.setAttribute('data-bs-placement', 'right');
            link.setAttribute('data-bs-title', 'Gérer les zones');
            break;
            case '/admin/masterdata/location/':
            link.setAttribute('data-bs-toggle', 'tooltip');
            link.setAttribute('data-bs-placement', 'right');
            link.setAttribute('data-bs-title', 'Gérer les locales');
            break;
            case '/admin/masterdata/emplacement/':
            link.setAttribute('data-bs-toggle', 'tooltip');
            link.setAttribute('data-bs-placement', 'right');
            link.setAttribute('data-bs-title', 'Gérer les emplacements');
            break;
            case '/admin/masterdata/departement/':
            link.setAttribute('data-bs-toggle', 'tooltip');
            link.setAttribute('data-bs-placement', 'right');
            link.setAttribute('data-bs-title', 'Gérer les departements');
            break;
            case '/admin/masterdata/personne/':
            link.setAttribute('data-bs-toggle', 'tooltip');
            link.setAttribute('data-bs-placement', 'right');
            link.setAttribute('data-bs-title', 'Gérer les personnes');
            break;
            case '/admin/masterdata/tag/':
            link.setAttribute('data-bs-toggle', 'tooltip');
            link.setAttribute('data-bs-placement', 'right');
            link.setAttribute('data-bs-title', 'Gérer les tags');
            break;

            case '/admin/masterdata/type_tag/':
            link.setAttribute('data-bs-toggle', 'tooltip');
            link.setAttribute('data-bs-placement', 'right');
            link.setAttribute('data-bs-title', 'Gérer les type du tags');
            break;
            case '/admin/masterdata/operation/':
            link.setAttribute('data-bs-toggle', 'tooltip');
            link.setAttribute('data-bs-placement', 'right');
            link.setAttribute('data-bs-title', 'Gérer les operations');
            break;
            case '/admin/masterdata/tagemplacement/':
            link.setAttribute('data-bs-toggle', 'tooltip');
            link.setAttribute('data-bs-placement', 'right');
            link.setAttribute('data-bs-title', 'Gérer les tags d \'emplacements');
            break;
            case '/admin/masterdata/emplacementtag/':
            link.setAttribute('data-bs-toggle', 'tooltip');
            link.setAttribute('data-bs-placement', 'right');
            link.setAttribute('data-bs-title', 'Affecter les tags à des emplacements');
            break;
            // Continuez à ajouter d'autres liens...   
        }
    });

    // Initialisez les tooltips Bootstrap
    const tooltipTriggerList = [].slice.call(sidebarLinks);
    tooltipTriggerList.forEach(function (tooltipTriggerEl) {
        new bootstrap.Tooltip(tooltipTriggerEl); // Créez une nouvelle instance de tooltip pour chaque lien
    });
});
