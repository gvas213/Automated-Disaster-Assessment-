goal

take these images and get the different image boundaries,

after that send it to a vlm and produce a json for that



1. first step crop the images using the boundaries from the json
2. send that to the vlm
3. assess the damage ( minor damage, mahor damage, destroyed, feature type )
4. compare accuracy to the original json


example output of the vlm

```JSON

{

"feature": "building/lot/land/farm/etc.",
"subtype": "minor-damage"


}

```
1. vlm will go through all image one by one
2. match with the json file (extract object and uid)
3. take coordinates and crop specific part of image both before and after
4. analyze the image with the vlm and determine damage
5. take the given json data and compare with the vlm predicted one (use the uid)
6. output some accuracy metric or something?
7. combine into json file 
