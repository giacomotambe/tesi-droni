from loguru import logger
from pprint import pprint
from mavsdk import System
import asyncio
from typing import List, Callable
from systemwrapper import SystemWrapper
from droneposition import DronePosition


class Swarm:
    """
    Inizializza una flotta di drones_number droni agli indirizzi
    specificati oppure ad indirizzi progressivi.

    Args:
        target_scanner (Callable[[System], float]): Funzione che prende
            in ingresso un drone e restituisce un intero in [0,1] che 
            rappresenta quanto quel drone sia vicino al target
        drones_number (int): Numero di droni da cui è composta la flotta
        drones_addrs (List[int], optional): Indirizzi dei droni.
            Defaults to None.
    Attributes:

    Raises:
        ValueError: Il numero di droni deve corrispondere al numero
        di elementi di drone_addrs
    """
    # indirizzo del prossimo drone creato (incrementata dopo la creazione di ciascun drone)
    # la variabile è condivisa da tutte le istanze della classe così da poter
    # creare più Swarm senza conflitti
    next_drone_address = 14540 
    def __init__(self,
                target_scanner:Callable[[System], float],
                drones_number:int,
                drones_addrs:List[int]=None) -> None:
        self.__target_scanner = target_scanner
        self.__discoveries:List[float] = []
        self.__drones_number = drones_number
        self.__positions = []
        self.__drones:List[System] = []

        # se non viene passata una lista di indirizzi vengono usati quelli di 
        # default a partire da next_drone_address
        if drones_addrs == None:
            self.drones_addrs = []
            for i in range(drones_number):
                self.drones_addrs.append(Swarm.next_drone_address)
                Swarm.next_drone_address += 1
        elif drones_number != len(drones_addrs):
            raise ValueError; "The number of drones specified does not match with the list size"
        else:
            self.drones_addrs = drones_addrs
        logger.info(f"Creating swarm with {self.__drones_number} drones at {self.drones_addrs}")


    async def connect(self):
        """
        Permette di connettersi a ciascun drone simultaneamente.
        """
        logger.info("Connecting to drones...")
        for a in self.drones_addrs:
            logger.info(f"Connecting to drone@{a}")
            sysW = SystemWrapper(a)
            drone = await sysW.connect()
            logger.info(f"Coonection to drone@{a} completed")
            self.__drones.append(drone)

    async def takeoff(self):
        """
        Fa decollare tutti i droni simultaneamente.
        """
        #TODO controllare se i droni sono connessi 
        logger.info("Taking off")
        for d in self.__drones:
            await d.action.arm()
            await d.action.takeoff()
        logger.info("Takeoff completed")

    async def land(self):
        """
        Fa atterrare tutti i droni simultaneamente.
        """
        logger.debug("Landing")
        for d in self.__drones:
            await d.action.land()
        logger.debug("Landing completed")

    @property
    async def positions(self) -> List[DronePosition]:
        """
        Restituisce una lista con le posizioni dei droni

        Returns:
            List[DronePosition]: Posizioni correnti dei singoli droni 
        """
        self.__positions = []
        for d in self.__drones:
            p = await anext(d.telemetry.position())
            pos = DronePosition.from_mavsdk_position(p)
            self.__positions.append(pos)

        return self.__positions
    
    async def set_positions(self, target_positions:List[DronePosition]):
        """
        Fa spostare i droni alle posizioni indicate in `target_positions`

        Args:
            target_positions (List[DronePosition]): Lista di posizioni a cui
                far muovere i droni
        """
        prev_pos = await self.positions
        print(prev_pos)
        for n, d in enumerate(self.__drones):
            pos = target_positions[n]
            logger.info(f"Moving drone@{self.drones_addrs[n]} to {pos}")
            await d.action.goto_location(*pos.to_goto_location(prev_pos[n]))
    
    async def do_for_all(self, function:Callable):
        for d in self.__drones:
            function(d)

    @property
    async def discoveries(self) -> List[float]:
        """
        Restituisce le discovery di ciascun drone.

        Una discovery è un numero compreso tra 0 e 1 che indica quanto il drone
        sia "vicino" all'obiettivo, 1 indica che l'obiettivo è stato trovato

        Returns:
            List[float]: Lista delle discovery per ciascun drone
        """
        self.__discoveries = []
        for d in self.__drones:
            self.__discoveries.append(await self.__target_scanner(d))

        return self.__discoveries

        