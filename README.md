https://www.python.org/downloads/


pip install osmium pgeocode geopy

lade eine PBF Datei herunter welche den relevanten Bereich enthält.
Wenn die Datei zu groß wird, dauert es irgendwann sehr lange. ich arbeite meist mit rund 210MB. Das funktioniert noch recht schnell (ca. 1 Minuten import ohne Klettersteige).
Mit 460MB ist auch noch OK aber dauert schon deutlich länger (Import ohne Klettersteige dauert schon ca. 2min 20 Sekunden mit  Ryzen 7 5700G)
Ich habe die Karte hier exportiert: https://extract.bbbike.org/  
fähige Leute würde es wahrscheinlich selbst mittels Python aus der Europakarte exportieren

Die Klettersteigsuche, sucht einfach, bei welchen Gipfel ein Klettersteig in der Nähe ist. 
wenn die Distanz gering gesetzt wird, werden eher jene Gipfel angezeigt, wo der Klettersteig direkt hin führt. wenn der weit weiter gesetzt wird, könnten auch benachbarte Klettersteige angezeigt werden. 
