# tesi-droni
docker run -it --privileged -v /tmp/.X11-unix:/tmp/.X11-unix:ro -e DISPLAY=:0 --network host --name=prova6 giacomotambellini/ambiente_droni_px4:0.1

- una volta creato il container, il sistema ubuntu avrà già un utente 'user' al suo interno con password 'user', mentre la password dell'utente root è 'root'

- all'interno della cartella /tesi-droni sono contenuti le classi python da utilizzare per la programmazione

- all' interno del dockerfile c'è il codice per la creazione dell'immagine, con tutti i pacchetti installati

- per lanciare la simulazione di droni:
  $ cd /PX4-Autopilot \\
  $ sudo ./Tools/simulation/sitl_multiple_run.sh 2 \\
  $ sudo ./Tools/simulation/jmavsim/jmavsim_run.sh -l \\
  $ sudo ./Tools/simulation/jmavsim/jmavsim_run.sh -p 4561 -l \\

