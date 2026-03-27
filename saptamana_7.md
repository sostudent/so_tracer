## probleme in fuctie de nivelul de cunostinte

# nivelul 0
Un proces care creaza alt proces iar noul proces creat afiseaza pidul procesului parinte

# nivelul 1
Un proces care creaza alt proces, iar noul proces creaza alt proces la randul lui, iar al treilea proces afiseaza pidurile proceselor anterioare in ordine, adica pid proces 1 si apoi pid proces 2

# nivel 2
Un proces care creaza doua procese, apoi cele doua procese la randul lor creaza alt proces, si ultimele doua procese afiseaza pidurile proceselor parinte in ordinea in care au fost create

# nivel 3
Un proces care creaza doua procese, apoi cele doua procese la randul lor creaza alte 3 procese, fiecare proces din cele 6 procese de la final afiseaza pidurile proceselor parinte in ordinea in care au fost create

# nivel 4
Un proces care creaza doua procese, apoi cele 2 procese creaza la randul lor alte 3 procese, iar fiecare din cele 6 procese de la final afiseaza pidurile proceselor care nu au fost parinte direct dar au fost unul din cele doua proese create la nivelul 2

# nivel 5
Un proces care creaza trei procese, apoi cele 3 procese creaza la randul lor alte 3 procese, iar fiecare din cele 9 procese de la final afiseaza pe 4 linii
 - pidul primului proces
 - pidul procesului parinte
 - pidurile celorlalte 8 procese de pe ultimul nivel (nu conteaza ordinea)
 - pidurile celorlalte 2 procese de pe nivelul 2 care nu sunt parintele direct (nu conteaza ordinea)
