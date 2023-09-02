from typing import List, Callable
from swarm import Swarm
import asyncio
import random
from droneposition import DronePosition
from loguru import logger
import math
import time
#la funzione create simulation fire inizializza la matrice di simulazione
#degli incendi in un area di dim_area km per dim_areakm intonro alla posizione iniziale
#dei droni
#la dimensione dell'inendio viene passata in numero di zone che sono
#state colpite dall'incendio

#dimensione dell'area pattugliata dai droni
dim_area=0
#latitudine massima dell'area
max_lat=0
#longitidine massima dell'area
max_long=0
#latitudine minina dell'area
min_lat=0
#longitudine minima dell'area
min_long=0


#area viene suddivisa in settori, ipotizzo che la dimensione di ogni settore coincide con la capacita del drone di verificare la presenza o meno di un incendio nella zona
#verifica che può essere eseguita con un sensore termico oppure una telecamera e un algoritmo di ricerca di fiamme all'interno di un immagine
#per comodità viene utilizzato come numero di settori un valore che posside una radice intera così da poter avere dei settori quadrati che riempono perfettamente l'area 
numero_settori=16
fire_map = [0]*numero_settori
numero_righe_colonne=math.sqrt(numero_settori)

#trasforma gradi in metri
def deg_to_m(deg) -> float:
    # 1 deg = 111319.9 m
    return deg * 111319.9
#trasforma metr in gradi
def m_to_deg(m) -> float:
    return m / 111319.9


#inizializza le variabili globali contenenti la dimensione dell'area 
#inizializza il vettore degli incendi,mettendo a 1 un numero di settori pari a 'dimensione_incendio'
async def create_simulation_fire(swarm:Swarm,len_track_zone,dimensione_incendio):
    start_pos = await swarm.positions
    center=start_pos[0]
    print(center)
    global dim_area
    dim_area= len_track_zone
    global max_lat
    #l'area di pattugliamento si estende a partire dalla posizione di iniziale dei droni
    max_lat = center.latitude_deg + m_to_deg(dim_area/2)
    global max_long
    max_long = center.longitude_deg + m_to_deg(dim_area/2)
    global min_lat
    min_lat = center.latitude_deg - m_to_deg(dim_area/2)
    global min_long
    min_long = center.longitude_deg - m_to_deg(dim_area/2)


    global fire_map
    fire_map = [0]*numero_settori


    focolaio = random.randint(0,numero_settori-1)
    print(focolaio)
    fire_map[focolaio]=1
    total_fire=0
        #si genera un numero casuale per simulare l'espansione del fuoco
        #il fuoco si potra espandere in zone adiacenti quindi sopra sotto destra o sinistra
        #se fire_zone = 0 l'incendio si propaga verso destra
        #se fire_zone = 1 l'incendio si propaga verso sinistra
        #se fire_zone = 2 l'incendio si propaga verso sotto
        #se fire_zone = 3 l'incendio si propaga verso sopra
    #l'incendio si propaga nelle zone vicine, per cui viene inizailmente generato un focolaio in una poisizione casuale, e sempre casualmente l'incendio si 
    #espanderà nelle celle adiacenti per un numero di volte pari a dim_incendio 
    while total_fire!=dimensione_incendio:
        fire_zone = random.randint(0,3)
        #ogni volta che si genera un numero casuale controlla se è possibile, l'espensione e se si setta la posizione dell'array
        if fire_zone == 0 and (focolaio+1)%numero_righe_colonne!=0:
            fire_map[focolaio+1]=1
            focolaio=focolaio+1
            total_fire+=1

        if fire_zone == 1 and focolaio%numero_righe_colonne!=0:
            fire_map[focolaio-1]=1
            focolaio=focolaio-1
            total_fire+=1
        if fire_zone == 2 and focolaio<numero_settori-numero_righe_colonne:
            fire_map[int(focolaio+numero_righe_colonne)]=1
            focolaio=int(focolaio+numero_righe_colonne)
            total_fire+=1
        if fire_zone == 3 and focolaio>numero_righe_colonne-1:
            fire_map[int(focolaio-numero_righe_colonne)]=1
            focolaio=int(focolaio-numero_righe_colonne)
            total_fire+=1
       # print(fire_zone,'-->',focolaio)
    print(fire_map)


#dato in ingresso una posizione restituisce il settore all'interno del quale si trova la posizione
def ricerca_settore(drone_pos:DronePosition):
    sect_dim=dim_area/numero_righe_colonne
    sect=0
    #data la posizione per ogni settore calcola la latitudine minima e massima e la longitudine minima e massima e controlla se la posizione di ingresso si trova all'interno del settore 
    for i in range(numero_settori):
        latitude_sect_min=m_to_deg((i%numero_righe_colonne)*sect_dim)+min_lat
        longitude_sect_max=max_long-m_to_deg(int(i/numero_righe_colonne)*sect_dim)        
        if drone_pos.latitude_deg>=latitude_sect_min and drone_pos.latitude_deg<latitude_sect_min+m_to_deg(sect_dim) and drone_pos.longitude_deg<=longitude_sect_max and drone_pos.longitude_deg>longitude_sect_max-m_to_deg(sect_dim):
            break
        sect+=1
    return sect

#ogni 10 secondi controlla se la posizione del drone coincide con la destinazione
#in caso affermativo si ferma, altrimenti attende altri 10 sec e rieffettua il controllo

async def wait_correct_position(sw,drones_pos_new:List[DronePosition]):
    mustend = time.time() + 60 #dopo un minuto di attesa di ricerca della posizione esce
    while time.time() < mustend:
        drones_pos_old = await sw.positions
        if correct_position(drones_pos_old,drones_pos_new): return True
        time.sleep(10)
    return False

#verifica che la distanza tra due posizioni sia minore di 2 metri
def correct_position(drones_pos_old:List[DronePosition],drones_pos_new:List[DronePosition]):
    for n,j in enumerate(drones_pos_new):
        dist=drones_pos_old[n].distance_2D_m(j)
        if dist > 2:
           return False
    return True

#una volta rilavato il primo settore incendiato la ricerca dell'incendio diventa ad albero, cioè per ogni settore incendiato vengono presi i sospetti che corripondono a le zone vicine
#e vengono inseriti nella lista dei sospetti, i quali verranno cotrollati perchè è probabile che ci sia un incendio
async def fire_mapping(sw:Swarm,k,num_drones):
    fire_suspect=[]
    fire_found=[]
    #vengono inizializzate le liste con l'incendio rilevato e i settori vicini(quelli da controllare)
    fire_found.append(k)
    sect_dim=dim_area/numero_righe_colonne
    if (k+1)%numero_righe_colonne!=0:
        fire_suspect.append(int(k+1))
    if k%numero_righe_colonne!=0:
        fire_suspect.append(int(k-1))
    if k>numero_righe_colonne-1:
        fire_suspect.append(int(k-numero_righe_colonne))
    if k<numero_settori-numero_righe_colonne:
        fire_suspect.append(int(k+numero_righe_colonne))

    new_pos = []
    old_pos = await sw.positions
    #ogni sospetto viene controllato da un drone che si sposta nel settore sospetto
    while fire_suspect:
        active_drones=0
        print("************************************")
        print("lista sospetti-->",fire_suspect)
        print("lista zone incendiate-->",fire_found)
        for i in range(num_drones):
            #nel caso in cui i settori sospetti rimasti siano minori del numero dei droni allora i droni liberi rimangono nel settore in cui si trovano
            #pronti nel caso venga trovato un incedio a controllare i vicini
            if fire_suspect:
                suspect=fire_suspect.pop(0)
                lat_suspect = min_lat+m_to_deg(sect_dim/2)+m_to_deg((suspect%numero_righe_colonne)*sect_dim)
                long_suspect = max_long-m_to_deg(sect_dim/2)-m_to_deg(int(suspect/numero_righe_colonne)*sect_dim)
                p=DronePosition(lat_suspect,long_suspect,old_pos[0].absolute_altitude_m)
                active_drones+=1
            else:
                p=old_pos[i].increment_m(0, 0, 0)
            new_pos.append(p)
        await sw.set_positions(new_pos)
        #per l'attesa sono state pensate 2 possibili soluzioni
        # 1-- calcolare il tempo data la distanza e un approssimazione della velocita, presa da QGroundControl
        # 2-- già speigata in precedenza, effettuare il polling

        #la scelta è ricaduta sul primo metodo perchè il polling causava dei blocchi improvvisi del programma
        max_dist=0
        for n,j in enumerate(new_pos):
            dist=old_pos[n].distance_2D_m(j)
            if dist>max_dist:
                max_dist= dist
        await asyncio.sleep(max_dist/3)
        #task=asyncio.create_task(wait_correct_position(sw,new_pos))
        #ret=await task
        #print("posizione corretta")
        #if not ret:
        #    print("ERRORE: END TIMEOUT")
        #    return fire_found
        old_pos=list(new_pos)
        new_pos.clear()
        disc = await sw.discoveries
        for n,j in enumerate(disc):
            if j==1 and n<active_drones:
                pos=await sw.positions
                fire = ricerca_settore(pos[n])
                fire_found.append(fire)
                #la scelta di inserire all'interno della lista quelli già controllati è perchè in un caso dinamico c'è rischio che l'incedio continui ad espandersi
                #nelle posizioni vicine per cui prima di tornare alla base i settori vicini vengono cotrollati più volte a  intervalli temporali diversi in modo
                #da controllare una possibile espanzione dell'incedio
                if (fire+1)%numero_righe_colonne!=0 and fire+1 not in fire_found and fire+1 not in fire_suspect:
                    fire_suspect.append(int(fire+1))
                if fire%numero_righe_colonne!=0 and fire-1 not in fire_found and fire-1 not in fire_suspect:
                    fire_suspect.append(int(fire-1))
                if fire>numero_righe_colonne-1 and fire-numero_righe_colonne not in fire_found and fire-numero_righe_colonne not in fire_suspect:
                    fire_suspect.append(int(fire-numero_righe_colonne))
                if fire<numero_settori-numero_righe_colonne and fire+numero_righe_colonne not in fire_found and fire+numero_righe_colonne not in fire_suspect:
                    fire_suspect.append(int(fire+numero_righe_colonne))
        #algoritmo finisce quando non ci sono più settori adiacenti all'incedio da controllare e restituisce un array contente il numero dei settori con un incedio
    return fire_found

#muove i droni alla posizione di partenza
async def return_to_home(sw:Swarm,original_pos):
    await sw.set_positions(original_pos)
    await asyncio.sleep(35)
    await sw.land()

#stampa a video l'area divisa in settori e le rispettiva coordinate. segna con una X i settori incendiati
def print_fire_map(fire_map:List[int]):
    print_string=[]
    for i in range(numero_settori):
        print_string.append(' ')
    for n,j in enumerate(fire_map):
        print_string[j]='X'
    sect_dim=dim_area/numero_righe_colonne
    print('')
    for i in range(int(numero_righe_colonne+1)):
        lat=str(min_lat+m_to_deg(int(i*sect_dim)))
        print(lat[:10],end='    ')
    print('')
    for i in range(int(numero_righe_colonne)):
        for k in range(int(14*numero_righe_colonne+1)):
            print('-', end='')

        print(max_long-m_to_deg(int(i/numero_righe_colonne)*sect_dim))
        for k in range(int(numero_righe_colonne+1)):
    	    print('|             ',end='')
        print('')
        print('|',end='      ')
        for j in range(int(numero_righe_colonne)):
            print(print_string[int(i*numero_righe_colonne+j)],end='      |      ') 
        print('')
        for k in range(int(numero_righe_colonne+1)):
    	    print('|             ',end='')
        print('')
    for i in range(int(14*numero_righe_colonne+1)):
        print('-', end='')
    print(min_long)
    print('')


#detection del drone, se il drone si trova sopra una zona incediata restiruisce 1 altrimenti 0 
async def fire_scanner(drone) -> float:

    #recupero la posizione del drone
    p = await anext(drone.telemetry.position())
    drone_pos = DronePosition.from_mavsdk_position(p)


    #se la posizione della zona incendiata rientra nel raggio di azione del drone segnala l'incendio
    i=ricerca_settore(drone_pos)
    print(i)
    fire_detection=0
    if fire_map[i]==1:
        fire_detection=1
    return fire_detection


async def main():
    drones_num=2
    sw = Swarm(fire_scanner,drones_num)
    await sw.connect()
    task1 = asyncio.create_task(create_simulation_fire(sw,200,3))
    await task1
    sect_dim=dim_area/numero_righe_colonne
    #inizializzazione imposta la posizione dei droni per il pattugliamento
    await sw.takeoff()
    await asyncio.sleep(20)
    original_pos = await sw.positions
    start_pos = []
    #sposta i droni nei settori di partenza cioè il primo va nel settore 0 e gli altri vengono messi sulla stessa riga
    for i in range(drones_num):
        lat_ini=min_lat+m_to_deg(sect_dim/2)
        long_ini=max_long-m_to_deg(i*sect_dim)-m_to_deg(sect_dim/2)
        p=DronePosition(lat_ini,long_ini,original_pos[i].absolute_altitude_m+20)
        start_pos.append(p)
    await sw.set_positions(start_pos)
    max_dist=0
    #attende che i droni siano nella corretta posizione
    for n,j in enumerate(start_pos):
        dist=original_pos[n].distance_2D_m(j)
        if dist>max_dist:
           max_dist= dist
    await asyncio.sleep(max_dist/3)
   # task=asyncio.create_task(wait_correct_position(sw,start_pos))
   # ret=await task
   # if not ret:
   #    print("ERROR: TIMEOUT")
   #    task6=asyncio.create_task(return_to_home(sw,original_pos))
   #   await task6
   #    return

    new_pos = await sw.positions
    examined_sect=0
    #direction=0 il drone si muove verso destra
    #sirection=1 il drone si muove verso sinistra
    #controlla il settore che corrisponde alla posizione attuale del drone, questo lo fa leggendo dal vettore restituito dalla discoveries
    direction=0
    new_pos=[]
    old_pos=start_pos
    disc = await sw.discoveries
    k=0
    for n,j in enumerate(disc):

        if j==1:
            break
        k+=1
    #nel caso in cui viene trovato un incendio viene chiamata fire_mapping che restituisce un array contenenti i settori incendiati, i droni tornano alla home e viene stampata la mappa degli incendi
    if k!=drones_num:
        fire_position = await sw.positions

        s=ricerca_settore(fire_position[k])
        print("incendio rilevato in",s)
        task7=asyncio.create_task(fire_mapping(sw,s,drones_num))
        final_map=await task7
        print(final_map)
        task6=asyncio.create_task(return_to_home(sw,original_pos))
        await task6
        print_fire_map(final_map)
        return
    else:
        print("incendio non rilevato")



    while examined_sect<numero_righe_colonne:
        #i droni vengono spostati sulla stessa colonna nel settore adiacente
        for i in range(int(numero_righe_colonne-1)):
            for n,p in enumerate(old_pos):
                if direction == 0:
                    new_pos.append(p.increment_m(sect_dim,0,0))
                else:
                    new_pos.append(p.increment_m(-sect_dim,0,0))
            await sw.set_positions(new_pos)
            max_dist=0
            for n,j in enumerate(new_pos):
                dist=old_pos[n].distance_2D_m(j)
                if dist>max_dist:
                    max_dist= dist
            await asyncio.sleep(max_dist/3)
           # task=asyncio.create_task(wait_correct_position(sw,new_pos))
           # ret=await task
           # if not ret:
           #     print("ERROR: TIMEOUT")
           #     task6=asyncio.create_task(return_to_home(sw,original_pos))
           #     await task6
           #     return
            old_pos=list(new_pos)
            new_pos.clear()


            #viene rieffetuato il controllo di incendio per ogni settore
            disc = await sw.discoveries
            k=0
            print(disc)
            for n,j in enumerate(disc):
                if j==1:
                    break
                k+=1

            if k!=drones_num:
               fire_position = await sw.positions
               s=ricerca_settore(fire_position[k])
               print("incendio rilevato in",s)
               task7=asyncio.create_task(fire_mapping(sw,s,drones_num))
               final_map=await task7
               print(final_map)
               task6=asyncio.create_task(return_to_home(sw,original_pos))
               await task6
               print_fire_map(final_map)
               return
            else:
                print("incendio non rilevato")

        examined_sect = examined_sect + drones_num
        #passare alle righe successive e invertire la direzione
        #e traslare sull'ultima riga della direzione di un numero di settori pari al numero di droni
        if direction ==  0:
            direction=1
        else:
            direction=0
        if examined_sect<numero_righe_colonne:
            for n,p in enumerate(old_pos):
                if ricerca_settore(p.increment_m(0,-drones_num*sect_dim,0))<numero_settori:
                    new_pos.append(p.increment_m(0,-drones_num*sect_dim,0))
                else:
                    new_pos.append(p.increment_m(0,0,0))
            await sw.set_positions(new_pos)
            task=asyncio.create_task(wait_correct_position(sw,new_pos))
            ret = await task
            if not ret:
                print("ERROR: TIMEOUT")

            old_pos=list(new_pos)
            new_pos.clear()
            
            disc = await sw.discoveries
            k=0
            print(disc)
            for n,j in enumerate(disc):
                if j==1:
                    break
                k+=1

            if k!=drones_num:
               fire_position = await sw.positions
               s=ricerca_settore(fire_position[k])
               print("incendio rilevato in",s)
               task7=asyncio.create_task(fire_mapping(sw,s,drones_num))
               final_map=await task7
               print(final_map)
               task6=asyncio.create_task(return_to_home(sw,original_pos))
               await task6
               print_fire_map(final_map)
               return
            else:
                print("incendio non rilevato")
    print("NON SONO STATI RILAVATI INCENDI") 
    await sw.set_positions(original_pos)
    await asyncio.sleep(40)
    await sw.land()
if __name__ == "__main__":
    asyncio.run(main())

