## arcconf getconfig

код, позволяющий представить вывод команды `arcconf getconfig 1` в т.ч. в json

## Пример использования

### Вызов с использованием конвейера
```
arcconf getconfig 1 | python ./arcconf_getconfig.py
```

### Вызов с вызовом `arcconf getconfig <ID>` внутри кода
```
python ./arcconf_getconfig.py
```

### Вызов с использованием дампа
```
arcconf getconfig 1 > ./out.txt
python ./arcconf_getconfig.py -i ./out.txt
```

### Вызов с отображением внутренней структуры парсерв
```
python ./arcconf_getconfig.py --raw
```

### Вызов без преобразования в JSON, в виде используемом python-кодом
```
arcconf getconfig 1 > ./out.txt
python ./arcconf_getconfig.py --print < ./out.txt
```
