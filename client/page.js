// Creation d'une carte dans la balise div "map", et positionne la vue sur un point donné et un niveau de zoom
var map = L.map('map').setView([48.10,-2.7], 7.4);

var selectedStations = [];  // Liste pour stocker les stations sélectionnées
var addCurveMode = false; // Indique si je veux comparer des stations ou simplement voir la courbe pour une seule station
var dates = [2018, 2019]; // date de debut et de fin
var indicateur = "Moyenne interannuelle (m3/s)"; // par défaut c'est la moyenne interannuelle
var agreg = false;
var markersList = []
var limiteNbStations = 12;
var permis = false; // booléen qui permet de sélectionner une station pour réinitialiser, après avoir séléctionné le nombre maximum des stations (voir window qui s'affiche)

var basicIcone = L.icon({
    iconUrl: 'images/marker-icon.png',
    shadowUrl:"images/marker-shadow.png",
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    tooltipAnchor:[16,-28],
    shadowSize:[41,41]
})
var redIcone = L.icon({
    iconUrl: 'images/marker-red.png',
    shadowUrl:"images/marker-shadow.png",
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    tooltipAnchor:[16,-28],
    shadowSize:[41,41]
})

var layersListe = [];

// Ajout d'une couche de dalles OpenStreetMap
L.tileLayer('http://{s}.tile.osm.org/{z}/{x}/{y}.png', {
     attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
     }).addTo(map);

document.addEventListener("DOMContentLoaded", function(){
    document.getElementById("addCompButton").checked = false;
    document.getElementById("agreg-stations").checked = false;
    document.getElementById("optionsSelect").value = "Moyenne interannuelle (m3/s)";
    document.getElementById("addCompButton").checked = false;
    if (selectedStations.length == 0 || permis){
        document.getElementById("addCompButton").setAttribute("disabled", "true");
    }

})
	 
function load_data () {
    clearMarkers()
    var xhr = new XMLHttpRequest();
    xhr.onload = function() {   // fonction callback
      // récupération des données renvoyées par le serveur
	  var data = JSON.parse(this.responseText);
      // boucle sur les enregistrements renvoyés
      for ( n = 0; n < data.length; n++ ) {
        // insertion d'un marqueur à la position, attachement d'une popup, capture de l'évènement "clic'
	    var marker = L.marker([data[n].Y, data[n].X]).addTo(map)
                .bindPopup(data[n].LbStationHydro)
                .addEventListener('click', onMarkerClick)
                .id_station_ancien_et_nouveau=data[n].CdStationHydroAncienRef+','+data[n].CdStationHydro;  // propriété personnalisée ajouté au marqueur

        markersList.push(marker)
      }
    };
    xhr.open('GET','/stations/?indicateur=' + indicateur,true);
    xhr.send();
}

function onMarkerClick(e) { 
    if (selectedStations.length < limiteNbStations || permis){   
        var stationId = e.target.id_station_ancien_et_nouveau;   
        var checkbox = document.getElementById('addCompButton');
        addCurveMode = checkbox.checked
        agreg = document.getElementById('agreg-stations').checked;

        if (agreg){
            selectedStations.push(stationId);
            layersListe.push(e);
        }
        else{
            if (addCurveMode) {
                selectedStations.push(stationId)
                addCurve();
                agreg = false; 
            } 

            else{
                for (var i = 0; i < layersListe.length; i++) {
                    layer = layersListe[i];
                    layer.target.setIcon(basicIcone);
                }                
                selectedStations = [stationId];
                afficheFormeDates();
                sendHydrometrieWithDates();
                addCompButton.style.display = true;
                document.getElementById("addCompButton").removeAttribute("disabled");
                agreg = false; 
            }
        }
        e.target.setIcon(redIcone);
        layersListe.push(e);
        permis = false;
    }
    else{
        window.alert("Vous avez atteint la limite de station à comparer. Veuillez réinitialiser ou cliquer sur une autre station pour réinitialiser");
        addCurveMode = false;
        document.getElementById("addCompButton").checked = false;
        document.getElementById("addCompButton").setAttribute("disabled", "true");
        permis = true;
    }
    
}
function agregStations(){
    if(selectedStations.length > 0){
        var confirmation = window.confirm("Êtes-vous sûr de vouloir continuer ?\nCela va potentiellement supprimer les graphiques déjà générés");
        if (confirmation){
            resetImage();
            agreg = true;            
            layersListe = [];
            document.getElementById('agreg-stations').checked = true;
        }
        else{
            document.getElementById('agreg-stations').checked = false;
        }
    }
    else{
        resetImage();
        agreg = true;
        document.getElementById("submit-agreg").removeAttribute("disabled");
        document.getElementById('agreg-stations').checked = true;
        
        layersListe = [];
    }


}

function afficheFormeDates(){
    var labelDates = document.createElement("label");
    labelDates.textContent = "Dates:   ";


    var selectBorneInf = document.createElement("select");
    selectBorneInf.id = "borneInf";
    selectBorneInf.name = "borneInf";

    var selectBorneSup = document.createElement("select");
    selectBorneSup.id = "borneSup";
    selectBorneSup.name = "borneSup";


    // On génère les options initiales
    for (var i = 2018; i < 2024; i++) {
        var optionInf = document.createElement("option");
        var optionSup = document.createElement("option");

        optionInf.value = i;
        optionSup.value = i + 1;

        optionInf.text = i;
        optionSup.text = i + 1;

        selectBorneInf.add(optionInf);
        selectBorneSup.add(optionSup);
    }
    // On met à jour dynamiquement les options de la borne supérieure
    selectBorneInf.addEventListener("change", function () {
        // Supprimer toutes les options actuelles
        while (selectBorneSup.options.length > 0) {
            selectBorneSup.remove(0);
        }

        // On génère les nouvelles options en fonction de la borne inférieure sélectionnée
        var selectedInf = parseInt(selectBorneInf.value, 10);
        for (var i = selectedInf + 1; i <= 2024; i++) {
            var optionSup = document.createElement("option");
            optionSup.value = i;
            optionSup.text = i;
            selectBorneSup.add(optionSup);
        }
    });
    selectBorneInf.style.marginRight = "5px"; // Ajout de marge en haut


    // Formulaire
    var form = document.createElement("form");
    form.appendChild(labelDates);
    form.appendChild(selectBorneInf);
    form.appendChild(selectBorneSup);

    // On ajoute le formulaire à #reponse
    var formContainerDiv = document.getElementById("form-container");
    formContainerDiv.innerHTML = ""; // Effacer le contenu existant
    formContainerDiv.appendChild(form);

    // On attache un gestionnaire d'événements pour le formulaire
    selectBorneInf.value = dates[0];
    selectBorneSup.value = dates[1];
    form.addEventListener("change", function (event) {
        event.preventDefault(); // On empêche l'envoi du formulaire par défaut
        dates[0] = document.getElementById("borneInf").value;
        dates[1] = document.getElementById("borneSup").value;
        if (addCurveMode || permis){
            addCurve()
        }
        else{
            if (agreg){
                submitAgreg()
            }
            else{
                sendHydrometrieWithDates();
            }
        }
    });
}

function sendHydrometrieWithDates() {
    // Récupérer les valeurs sélectionnées dans les listes déroulantes
    var selectedBorneInf = dates[0];
    var selectedBorneSup = dates[1];

    // On construit la requête GET avec les dates sélectionnées
    station = selectedStations[0];
    var requestURL = '/hydrometrie/' + station + '?indicateur=' + indicateur + '&borneInf=' + selectedBorneInf + '&borneSup=' + selectedBorneSup;
    // Exécuter la requête AJAX
    var xhr = new XMLHttpRequest();
    xhr.onload = function () {
        // fonction callback
        var data = JSON.parse(this.responseText);

        // Mettre à jour le contenu de #reponse avec le graphique
        var image = document.querySelector('#reponse img'),
        legende = document.querySelector('#reponse p');
        maxValParagraph = document.getElementById('max_val'),
        minValParagraph = document.getElementById('min_val');
        image.src = data.img;
        image.alt = data.title;
        legende.innerHTML = data.title;
        
        // Affichage des statistiques
        maxValParagraph.innerHTML = 'Valeur maximale : ' + data.max_val;
        minValParagraph.innerHTML = 'Valeur minimale : ' + data.min_val;  
        image.classList.add('show');      
    };
    
    xhr.open('GET', requestURL, true);
    xhr.send();
}


function activateAddCurve(){
    addCurveMode = true;
}

function addCurve() {
    var selectedBorneInf = dates[0]; 
    var selectedBorneSup = dates[1];

    // On évite la redondance
    selectedStations = [...new Set(selectedStations)];

    // On construit la requête GET avec les dates sélectionnées
    var requestURL = '/hydrometrie/' + '?indicateur=' + indicateur + '&station_0=' + selectedStations[0]
    for (let i = 1; i < selectedStations.length; i++){
        requestURL += "&station_" + i +'=' + selectedStations[i];
    }
    requestURL += '&borneInf=' + selectedBorneInf + '&borneSup=' + selectedBorneSup;

    // Exécuter la requête AJAX
    var xhr = new XMLHttpRequest();
    xhr.onload = function () {
        // fonction callback
        var data = JSON.parse(this.responseText);

        // Mettre à jour le contenu de #reponse avec le graphique
        var image = document.querySelector('#reponse img'),
            legende = document.querySelector('#reponse p');
            maxValParagraph = document.getElementById('max_val'),
            minValParagraph = document.getElementById('min_val');
        image.src = data.img;
        image.alt = data.title;
        legende.innerHTML = data.title;
        
        // Affichage des statistiques
        maxValParagraph.innerHTML = 'Valeur maximale : ' + data.max_val;
        minValParagraph.innerHTML = 'Valeur minimale : ' + data.min_val;
        image.classList.add('show');
    };
    
    xhr.open('GET', requestURL, true);
    xhr.send();
}


// Fonction pour afficher l'option sélectionnée
function SelectOption(event) {
    event.preventDefault(); // Prevent the default form submission behavior
    var selectedValue = document.getElementById('optionsSelect').value;
    indicateur = selectedValue;

    var xhr = new XMLHttpRequest();
    if(selectedStations.length > 0){
        
        xhr.open('GET','/stations/?indicateur=' + indicateur,true);
        xhr.send();
    }
    // On réaffiche les courbes
    if (addCurveMode || permis){
        addCurve();
    }
    else{
        if (agreg){
            submitAgreg();
        }
        else{
            if(selectedStations.length > 0){
                sendHydrometrieWithDates();
            }
        }
    }
}

function resetImage() {
    var image = document.querySelector('#reponse img');
    var legende = document.querySelector('#reponse p');
    var legende = document.querySelector('#reponse p');
    var maxVal = document.getElementById('max_val');
    var minVal = document.getElementById('min_val');

    image.src = "";
    image.alt = "";
    legende.innerHTML = "";
    maxVal.innerHTML = ""; 
    minVal.innerHTML = ""; 

    var bouton = document.getElementById('agreg-stations');
    bouton.checked = false;


    selectedStations = []; 
    var checkbox = document.getElementById('addCompButton');
    checkbox.checked = false;

    addCurveMode = false;
    dates = [2018, 2019];
    agreg = false;
    document.getElementById("addCompButton").setAttribute("disabled", "true");
    for (var i = 0; i < layersListe.length; i++) {
        layer = layersListe[i];
        layer.target.setIcon(basicIcone);
    }
}

function SetComp(){
    var checkbox = document.getElementById('addCompButton');
    addCurveMode = checkbox.checked;
}

function submitAgreg(){
    // on deselectionne l'option
    var bouton = document.getElementById('agreg-stations');
    bouton.checked = false;

    var selectedBorneInf = dates[0]; 
    var selectedBorneSup = dates[1];
    if (selectedStations.length > 0){

        // On construit la requête GET avec les dates sélectionnées
        var requestURL = '/agreg/' + '?indicateur=' + indicateur + '&station_0=' + selectedStations[0]
        for (let i = 1; i < selectedStations.length; i++){
            requestURL += "&station_" + i +'=' + selectedStations[i];
        }
        requestURL += '&borneInf=' + selectedBorneInf + '&borneSup=' + selectedBorneSup;

        // Exécuter la requête AJAX
        var xhr = new XMLHttpRequest();
        xhr.onload = function () {
            // fonction callback
            var data = JSON.parse(this.responseText);

            // Mettre à jour le contenu de #reponse avec le graphique
            var image = document.querySelector('#reponse img'),
                legende = document.querySelector('#reponse p');
                maxValParagraph = document.getElementById('max_val'),
                minValParagraph = document.getElementById('min_val');
            image.src = data.img;
            image.alt = data.title;
            legende.innerHTML = data.title;
            
            // Affichage des statistiques
            maxValParagraph.innerHTML = 'Valeur maximale : ' + data.max_val;
            minValParagraph.innerHTML = 'Valeur minimale : ' + data.min_val;

            image.classList.add('show');

        };
        
        xhr.open('GET', requestURL, true);
        xhr.send();

        var checkbox = document.getElementById('addCompButton');
        checkbox.checked = false;
        document.getElementById("addCompButton").setAttribute("disabled", "true");
    }
    else {
        window.alert("Veuillez sélectionner des stations avant de valider l'agrégation.");
    }

}

function clearMarkers() {
    markersList.forEach(function(marker) {
        map.removeLayer(marker);
    });

    markersList = [];
}

afficheFormeDates();
afficheFormeIndicateurs();