# GmE 205: FInal Project 
## Object-Oriented GIS-Based Healthcare Accessibility System Using OD-Cost Matrix and 2SFCA Model: A Case Study of UP Diliman Dormitories, Quezon City, Philippines

### *Description*
This project developed an Object-Oriented GIS-based Healthcare Accessibility System for UP Diliman dormitories in QUezon City, Philippines, using Python, GeoPandas, NetworkX, Shapely, and Folum. Thee system aims to evaluate healthcare accessbility by modeling the road network as a directed graph, computing shortest travel times through an Origin-Destination (OD) Cost Matrix, and applying the Two-Step Floating Catchment Area (2SFCA) model to incorporate heathcare facility capcity and population demand. Using GeoJSON datasets of dormitories, healthcare facilities, and road networks, the system identified the nearest healthcare facility for each dormitory, calculated accessibility indices within a 15-minute travel-time threshold, and generated interactive maps and JSON-based summaries. Results showeed that UP Health Services was the nearest facility for 11 of the 13 dormitories, while Centennial Dormitory and Kamagong Residence Hall achieved the highest accessbility indices due to access to a greater number of healthcare facilities and higher-capacity hospitals. Overall, the system demonstrates how Object-Oriented Programming (OOP) and GIS-based network analysis can support healthcare accessibility assessment and spatial decision-making in pursuit of Sustainable Development Goal 3.

### *Technologies/Tools Used*
* Python 3.14 - Programming language used in VS Code that will support the OOP model
* Visual Studio Code - Source code editor
* GeoPandas - Library for reading, processing, and managing spatial and GeoJSON datasets
* NetworkX - Library for road-network analysis used in OD Cost Matrix and closest-facility computation
* Shapely - Library for geometric operations and spatial object manipulation
* Folium - Library for developing interactive GIS-based web maps

### *Objectives*
This project aims to develop an object-oriented GIS-Based healthcare accessbility system that evaluates dormitory access to healthcare facilities in UP Diliman using OD Cost Matrix and the Two-Step Floating Catchment Area (2SFCA) model. Specifically, this project ought to:<br>
1. Implement real travel-time OD Cost Matrix and closest-facility analysis using NetworkX road-netowrk routing.<br>
2. Apply the Two-Step Floating Catchment Area (2SFCA) model to compute healthcare accessibility indices based on healthcare facility capacity and population demand.<br>
3. Develop an interactive healthcare accessibiilty map using GeoPandas and Folium, which shows the result from the OD-Cost Matrix and Accessbility Index analysis.<br>

### *System Design and Workflow*
#### *Input*
* Dorm.geojson
* HCF.geojson
* Roads.geojson
#### *Processing Workflow*
1. Load GeoJSON datasets<br>
2. Filter non-drivable road segments<br>
3. Build a directed road network using NetworkX<br>
4. Snap dormitories and healthcare facilities to the nearest road nodes<br>
5. Generate an Origin-Destination (OD) Cost Matrix using Dijkstra's Algorithm<br>
6. Apply 2SFCA Step 1 to calculate hospital supply-to-demand ratios (Rⱼ)<br>
7. Apply 2SFCA Step 2 to calculate dormitory accessibility indices (Aᵢ)<br>
#### *Output*
* Interactive Map showing OD-Cost Matrix, Accessibility Indices, and Closest Healthcare Facility.
* Summary (JSON file) containing healthcare facility information, supply-to-demand ratios (Rⱼ), accessibility indices (Aᵢ), closest healthcare facilities, travel times, and reachable facilities for each dormitory.

## Author
Maria Graciella L. Roque  
Discord:[@grachiebob]

## Acknowledgements
* GmE 205 Laboratory Exercise Manual
* [MarkDown](https://www.markdownguide.org/cheat-sheet/)

Edited on VS Code