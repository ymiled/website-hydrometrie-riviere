# -*- coding: utf-8 -*-
"""
Serveur web permettant d'afficher les courbes d'hydrométrie des stations bretonnes'


@author: D2AD
"""

import http.server
import socketserver
from urllib.parse import urlparse, parse_qs, unquote
import json

import datetime as dt
import sqlite3

import matplotlib.pyplot as plt
import matplotlib.dates as pltd

# numéro du port TCP utilisé par le serveur
port_serveur = 8081
class RequestHandler(http.server.SimpleHTTPRequestHandler):
  """"Classe dérivée pour traiter les requêtes entrantes du serveur"""

  # sous-répertoire racine des documents statiques
  static_dir = 'client'
  
  def __init__(self, *args, **kwargs):
    """Surcharge du constructeur pour imposer 'client' comme sous répertoire racine"""
    super().__init__(*args, directory=self.static_dir, **kwargs)
    

  def do_GET(self):
    """Traiter les requêtes GET (surcharge la méthode héritée)"""

    # On récupère les étapes du chemin d'accès
    self.init_params()

    # le chemin d'accès commence par /stations
    if self.path_info[0] == 'stations':
      self.send_stations()
      
    # le chemin d'accès commence par /hydrometrie
    elif self.path_info[0] == 'hydrometrie':
      self.send_hydrometrie()
    
    elif self.path_info[0] == 'agreg':
      self.send_agreg()
    

    # sinon appel de la méthode parente...
    else:
      super().do_GET()
    
       
  def send_stations(self):
    """Génèrer une réponse avec la liste des stations """
    indicateur = self.params['indicateur'][0]
 
    # création du curseur (la connexion a été créée par le programme principal)
    c = conn.cursor()
    # récupération de la liste des régions et coordonnées (import de stations.csv)
    c.execute("SELECT CdStationHydroAncienRef, CdStationHydro, X,Y,LbStationHydro FROM 'stations'")
    r = c.fetchall()
        
    # traite la table et enlève les données non existantes dans une des tables
    #c.execute(f'SELECT DISTINCT "Code site Hydro3" FROM hydrometrie WHERE SUM("{indicateur}") IS NOT NULL')
    c.execute(f'SELECT DISTINCT "Code site Hydro3" FROM hydrometrie WHERE "{indicateur}" IS NOT NULL')
    stations_hydrometrie = c.fetchall()
    r = [station for station in r if (station[0], ) in stations_hydrometrie or (station[1], ) in stations_hydrometrie]   
      
    body = json.dumps([{'CdStationHydroAncienRef':iid_ancien, 'CdStationHydro':iid_nouveau, 'X':lat, 'Y': lon, 'LbStationHydro':nom} 
                       for (iid_ancien, iid_nouveau, lat, lon, nom) in r])    

    # envoi de la réponse
    headers = [('Content-Type','application/json')]
    self.send(body,headers)

  def send_hydrometrie(self):
    """Générer un graphique d'hydrométrie et une réponse HTML avec balise IMG"""

    # création du curseur (la connexion a été créée par le programme principal)
    c = conn.cursor()
    stations = []
    
    # si pas de paramètre => plusieurs stations spécifiées
    if len(self.path_info) <= 1 or self.path_info[1] == '':
      # on récupère l'id de toutes les stations spécifiées
      stations = []
      noms_stations = []
      i = 0
      while f'station_{i}' in self.params and i < 50:
        stations.append(self.params[f'station_{i}'][0])   
        i += 1
      
      for i in range(len(stations)):
        s = stations[i]
        s_ancien = s.split(',')[0]
        s_nouveau = s.split(',')[1]
        # On teste que la station demandée existe bien
        c.execute('SELECT DISTINCT "Code site Hydro3" FROM hydrometrie')
        r = c.fetchall()
        
        stations[i] = s_ancien # on prend par défaut la station avec l'ancien id
        if (stations[i],) not in r:
          # Si l'identifiant ancien n'existe pas, on prend le nouvel identifiant
          stations[i] = s_nouveau
          
          # Si la station n'est juste pas reconnue :        
          if (stations[i],) not in r:
            # Station non trouvée -> erreur 404
            print ('Erreur station inconnue')
            self.send_error(404)    
            return 
        c.execute('SELECT DISTINCT CdStationHydroAncienRef,LbStationHydro FROM stations')
        r=c.fetchall()
        for couple in r:
          if couple[0] == stations[i]:
            noms_stations.append(couple[1])
            
              
    else:          
        # on récupère l'id de la station dans le 1er paramètre
        station_ancien = self.path_info[1].split(',')[0]
        station_nouveau = self.path_info[1].split(',')[1]
        # On teste que la station demandée existe bien
        c.execute('SELECT DISTINCT "Code site Hydro3" FROM hydrometrie')
        r = c.fetchall()
        # Remarque : r est une liste de tuples à 1 seul élement
        
        stations = [station_ancien] # on prend par défaut la station avec l'ancien id
        noms_stations = []
        if (stations[0],) not in r:
          # Si l'identifiant ancien n'existe pas, on prend le nouvel identifiant
          stations[0] = station_nouveau
          
          # Si la station n'est juste pas reconnue :        
          if (stations[0],) not in r:
            # Station non trouvée -> erreur 404
            print ('Erreur station inconnue')
            self.send_error(404)    
            return
        

        # On récupère le nom de la station
        c.execute('SELECT DISTINCT CdStationHydroAncienRef,LbStationHydro FROM stations')
        r=c.fetchall()
        for couple in r:
            if couple[0]==stations[0]:
                noms_stations.append(couple[1])
    
    # les dates entre le début et la fin sur l'absisse sont détérminées par la première 
    # station dans les paramètres (on a la même absisse pour toutes les stations sur le graphique)    
    station = stations[0]
    if 'borneInf' and 'borneSup' in self.params:
      debut = int(self.params['borneInf'][0])#list(map(int, self.params['borneInf'][0].split('-')))
      fin = int(self.params['borneSup'][0])#list(map(int, self.params['borneSup'][0].split('-')))
    else:
      debut = 2018
      fin = 2019
        
    # configuration du tracé
    indicateur = self.params['indicateur'][0]
    indices_indicateurs = {"Moyenne interannuelle (m3/s)": 2, "Valeur forte (m3/s)": 3, "Valeur faible (m3/s)": 4}
    indice = indices_indicateurs[indicateur]

    # on détérmine la limite en y :
    maxi_y = 0 
    mini_y = float('inf')
    for i in range(len(stations)):
      c.execute("SELECT * FROM hydrometrie WHERE [Code site Hydro3] = ? ORDER BY Date", (stations[i],))
      r = c.fetchall() 
      y = [float(a[indice]) for a in r if not a[indice] == '' and debut <= int(a[0][6:]) < fin] 
      if maxi_y < max(y):
        maxi_y = max(y) 
      if mini_y > min(y):
        mini_y = min(y)
        
    
    plt.figure(figsize=(18,6))
    plt.ylim(0,maxi_y*1.5)
    plt.grid(which='major', color='#888888', linestyle='-')
    plt.grid(which='minor',axis='x', color='#888888', linestyle=':')
    
    ax = plt.subplot(111)
    loc_major = pltd.YearLocator()
    loc_minor = pltd.MonthLocator()
    ax.xaxis.set_major_locator(loc_major)
    ax.xaxis.set_minor_locator(loc_minor)
    format_major = pltd.DateFormatter('%d %B %Y')
    ax.xaxis.set_major_formatter(format_major)
    ax.xaxis.set_tick_params(labelsize=10)    
        
    c.execute("SELECT * FROM hydrometrie WHERE [Code site Hydro3] = ? ORDER BY Date", (station,))
    r = c.fetchall()    
    
    x = [pltd.date2num(dt.date(int(a[0][6:]), int(a[0][3:5]), int(a[0][:2]))) for a in r if not a[6] == '' and debut <= int(a[0][6:]) < fin]    

    for i in range(len(stations)):
      c.execute("SELECT * FROM hydrometrie WHERE [Code site Hydro3] = ? ORDER BY Date", (stations[i],))
      r = c.fetchall()
           
      y = [float(a[indice]) for a in r if not a[indice] == '' and debut <= int(a[0][6:]) < fin]  
      #on ajuste les dimensions :
      while(len(y) < len(x)):
          y.append(y[-1])
      # tracé de la courbe
      plt.plot_date(x, y, label=noms_stations[i]) 
    
    #légendes :
    plt.legend()
    plt.title(f'Hydrometrie des rivières', fontsize=16)  
    
    plt.ylabel(indicateur)
    plt.xlabel('Date')
    
    # génération de la courbe dans un fichier PNG paramétré par le nom des stations
    fichier = 'courbes/hydrometrie'
    fichier += f'_{indice}_'
    for s in stations:
      fichier += f'_{s}_'
      
    fichier += f'{debut}_{fin}.png'
     
    plt.savefig('client/{}'.format(fichier))

    # réponse au format JSON
    info = {
          "title": f'Historique des débits',
          "img" :	'/'+fichier,
          "max_val": "{:.2g}".format(maxi_y),
          "min_val": "{:.2g}".format(mini_y),
    }
    body = json.dumps(info)
    
    header = [('Content-Type', 'text/html;charset=utf-8')]
    self.send(body, header)
    
  def send_agreg(self):
    c = conn.cursor()
    stations = []
    
    # si pas de paramètre => plusieurs stations spécifiées
    if(len(self.path_info) <= 1 or self.path_info[1] == ''):
      # on récupère l'id de toutes les stations spécifiées
      stations = []
      noms_stations = []
      i = 0
      while f'station_{i}' in self.params and i < 50:
        stations.append(self.params[f'station_{i}'][0])   
        i += 1
      
      for i in range(len(stations)):
        s = stations[i]
        s_ancien = s.split(',')[0]
        s_nouveau = s.split(',')[1]
        # On teste que la station demandée existe bien
        c.execute('SELECT DISTINCT "Code site Hydro3" FROM hydrometrie')
        r = c.fetchall()
        
        stations[i] = s_ancien # on prend par défaut la station avec l'ancien id
        if (stations[i],) not in r:
          # Si l'identifiant ancien n'existe pas, on prend le nouvel identifiant
          stations[i] = s_nouveau
          
          # Si la station n'est juste pas reconnue :        
          if (stations[i],) not in r:
            # Station non trouvée -> erreur 404
            print ('Erreur station inconnue')
            self.send_error(404)    
            return 
        c.execute('SELECT DISTINCT CdStationHydroAncienRef,LbStationHydro FROM stations')
        r=c.fetchall()
        for couple in r:
          if couple[0] == stations[i]:
            noms_stations.append(couple[1])
            
    station = stations[0]
    if 'borneInf' and 'borneSup' in self.params:
      debut = int(self.params['borneInf'][0])#list(map(int, self.params['borneInf'][0].split('-')))
      fin = int(self.params['borneSup'][0])#list(map(int, self.params['borneSup'][0].split('-')))
    else:
      debut = 2018
      fin = 2019
        
    # configuration du tracé
    indicateur = self.params['indicateur'][0]
    indices_indicateurs = {"Moyenne interannuelle (m3/s)": 2, "Valeur forte (m3/s)": 3, "Valeur faible (m3/s)": 4}
    indice = indices_indicateurs[indicateur]
    
    c.execute("SELECT * FROM hydrometrie WHERE [Code site Hydro3] = ? ORDER BY Date", (station,))
    r = c.fetchall()    
    
    x = [pltd.date2num(dt.date(int(a[0][6:]), int(a[0][3:5]), int(a[0][:2]))) for a in r if not a[6] == '' and debut <= int(a[0][6:]) < fin]    
    y = [0 for _ in range(len(x))]
    
    for i in range(len(stations)):
      c.execute("SELECT * FROM hydrometrie WHERE [Code site Hydro3] = ? ORDER BY Date", (stations[i],))
      r = c.fetchall()
      # on récupère les valeurs de la station i
      valeurs_station = [float(a[indice]) for a in r if not a[indice] == '' and debut <= int(a[0][6:]) < fin]
      # on les rajoute dans y
      y = [acc + valeur for acc, valeur in zip(y, valeurs_station)]

    y = [acc / len(stations) for acc in y]
            
    plt.figure(figsize=(18,6))
    plt.ylim(0,max(y)*1.5)
    plt.grid(which='major', color='#888888', linestyle='-')
    plt.grid(which='minor',axis='x', color='#888888', linestyle=':')
    
    ax = plt.subplot(111)
    loc_major = pltd.YearLocator()
    loc_minor = pltd.MonthLocator()
    ax.xaxis.set_major_locator(loc_major)
    ax.xaxis.set_minor_locator(loc_minor)
    format_major = pltd.DateFormatter('%d %B %Y')
    ax.xaxis.set_major_formatter(format_major)
    ax.xaxis.set_tick_params(labelsize=10)    
        
    # légendes :
    label = f"Moyenne des stations {noms_stations[0]}"
    for i in range(1, len(noms_stations)-1):
        if i < 4:
            label += f", {noms_stations[i]}"
    if len(noms_stations) > 1:
        label += f" et {noms_stations[-1]}"
    
    plt.plot_date(x, y, label=label) 
    
    plt.legend()
    plt.title(f'Moyenne des {indicateur} des stations séléctionnée des rivières', fontsize=16)      
    plt.ylabel(indicateur)
    plt.xlabel('Date')
    
    # génération de la courbe dans un fichier PNG paramétré par le nom des stations
    fichier = 'courbes/hydrometrie_agregation_'
    fichier += f'_{indice}_'

    for s in stations:
      fichier += f'_{s}_'
      
    fichier += f'{debut}_{fin}.png'
     
    plt.savefig('client/{}'.format(fichier))

    # réponse au format JSON
    info = {
          "title": f'Historique des débits',
          "img" :	'/'+fichier,
          "max_val": "{:.2g}".format(max(y)),
          "min_val": "{:.2g}".format(min(y)),
    }
    body = json.dumps(info)
    
    header = [('Content-Type', 'text/html;charset=utf-8')]
    self.send(body, header)
               
    

  def send(self, body, headers=[]):
    """Envoyer la réponse au client avec le corps et les en-têtes fournis
    
    Arguments:
    body: corps de la réponse
    headers: liste de tuples d'en-têtes Cf. HTTP (par défaut : liste vide)
    """
    # on encode la chaine de caractères à envoyer
    encoded = bytes(body, 'UTF-8')

    # on envoie la ligne de statut
    self.send_response(200)

    # on envoie les lignes d'entête et la ligne vide
    [self.send_header(*t) for t in headers]
    self.send_header('Content-Length', int(len(encoded)))
    self.end_headers()

    # on envoie le corps de la réponse
    self.wfile.write(encoded)


  def init_params(self):
    """Analyse la requête pour initialiser nos paramètres"""

    # analyse de l'adresse
    info = urlparse(self.path)
    self.path_info = [unquote(v) for v in info.path.split('/')[1:]]
    self.query_string = info.query
    
    # récupération des paramètres dans la query string
    self.params = parse_qs(info.query)

    # récupération du corps et des paramètres (2 encodages traités)
    length = self.headers.get('Content-Length')
    ctype = self.headers.get('Content-Type')
    if length:
      self.body = str(self.rfile.read(int(length)),'utf-8')
      if ctype == 'application/x-www-form-urlencoded' : 
        self.params = parse_qs(self.body)
      elif ctype == 'application/json' :
        self.params = json.loads(self.body)
    else:
      self.body = ''

    # traces
    print('init_params|info_path =', self.path_info)
    print('init_params|body =', length, ctype, self.body)
    print('init_params|params =', self.params)


# Création de la connexion avec la base de données
conn = sqlite3.connect('bzh.sqlite')

# Instanciation et lancement du serveur
httpd = socketserver.TCPServer(("", port_serveur), RequestHandler)
print("Serveur lancé sur port : ", port_serveur)
httpd.serve_forever()

conn.close()



