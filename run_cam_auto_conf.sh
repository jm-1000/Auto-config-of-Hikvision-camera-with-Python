#!/bin/bash

CONFIG_HISTORY_FILE="cam_config_history"
DEFAULT_IP=192.168.1.64

SITE=$(dialog \
                --title "Configuration auto de Camera" \
                --inputbox "Site :" 8 40 3>&1 1>&2 2>&3)
LAST_CONFIG=($(grep -e "^$SITE " $CONFIG_HISTORY_FILE | tail -1))

SIZE_FORM=(15 60 10)
SIZE=(30 30 0)
ARGS=(
    "Actuelle IP de la camera :" 1 1 "$DEFAULT_IP" 1 "${SIZE[@]}"
    "Nouvelle IP de la camera :" 2 1 "${LAST_CONFIG[1]}" 2 "${SIZE[@]}"
    "Masque du reseau :" 3 1 "${LAST_CONFIG[2]}" 3 "${SIZE[@]}"
    "IP de la passerelle :" 4 1 "${LAST_CONFIG[3]}" 4 "${SIZE[@]}"
    "Nom de la camera :" 5 1 "${LAST_CONFIG[4]}" 5 "${SIZE[@]}"
    "Le mot de passe :" 6 1 "${LAST_CONFIG[5]}" 6 "${SIZE[@]}"
)

RESULT=$(dialog \
                --title "Configuration auto de Camera" \
                --form "Veuillez remplir les champs" "${SIZE_FORM[@]}" \
                "${ARGS[@]}" \
                2>&1 >/dev/tty)
clear
mapfile -t VALUES <<< "$RESULT"

SAVE=1
for value in "${VALUES[@]}"; do
    if [ -z "$value" ]; then 
        SAVE=0; 
    fi
done
if [ $SAVE -eq 1 ]; then
    echo "$SITE ${VALUES[1]} ${VALUES[2]} ${VALUES[3]} ${VALUES[4]} ${VALUES[5]}" \
    >> "$CONFIG_HISTORY_FILE"
fi

echo "Testant la connexion avec la caméra..."
ping -c 3 ${VALUES[0]} 2>&1 >/dev/null
if [ $? -eq 0 ]; then
    python3 cam_auto_config.py \
                                -I ${VALUES[0]} \
                                -i ${VALUES[1]} \
                                -m ${VALUES[2]} \
                                -g ${VALUES[3]} \
                                -n ${VALUES[4]} \
                                -p ${VALUES[5]}
else echo "Erreur: Pas de connexion réseau avec la caméra."
fi