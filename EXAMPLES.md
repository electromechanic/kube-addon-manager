AWS Usage:

```
REGION=us-west-2
CLUSTER=dev-cluster
```

Install all addons enabled in config file

```
addon_manager.py --config-file config.yaml \
aws \
-a create \
-n all \
-r $REGION \
-c $CLUSTER 
```

Upgrade all addons enabled in config file

```
addon_manager.py --config-file config.yaml \
aws \
-a upgrade \
-n all \
-r $REGION \
-c $CLUSTER 
```

Delete all addons enabled in config file

```
addon_manager.py --config-file config.yaml \
aws \
-a delete \
-n all \
-r $REGION \
-c $CLUSTER 
```

Install a specific addon (pgadmin)

```
addon_manager.py --config-file config.yaml \
aws \
-a create \
-n pgadmin \
-r $REGION \
-c $CLUSTER 
```

Upgrade a specific addon (pgadmin)

```
addon_manager.py --config-file config.yaml \
aws \
-a upgrade \
-n pgadmin \
-r $REGION \
-c $CLUSTER 
```

Delete a specific addon (pgadmin)

```
addon_manager.py --config-file config.yaml \
aws \
-a delete \
-n pgadmin \
-r $REGION \
-c $CLUSTER 
```

GCP Usage:

```
REGION=us-central1
CLUSTER=sisu-dev-us-central1-gke-ahjxov
PROJECT=sisu-id-tdq8zr
```

Install all addons enabled in config file

```
addon_manager.py --config-file config.yaml \
gcp \
-a create \
-n all \
-r $REGION \
-c $CLUSTER \
-p $PROJECT
```

Upgrade all addons enabled in config file

```
addon_manager.py --config-file config.yaml \
gcp \
-a upgrade \
-n all \
-r $REGION \
-c $CLUSTER \
-p $PROJECT
```

Delete all addons enabled in config file

```
addon_manager.py --config-file config.yaml \
gcp \
-a delete \
-n all \
-r $REGION \
-c $CLUSTER \
-p $PROJECT
```

Install a specific addon (pgadmin)

```
addon_manager.py --config-file config.yaml \
gcp \
-a create \
-n pgadmin \
-r $REGION \
-c $CLUSTER \
-p $PROJECT
```

Upgrade a specific addon (pgadmin)

```
addon_manager.py --config-file config.yaml \
gcp \
-a upgrade \
-n pgadmin \
-r $REGION \
-c $CLUSTER \
-p $PROJECT
```

Delete a specific addon (pgadmin)

```
addon_manager.py --config-file config.yaml \
gcp \
-a delete \
-n pgadmin \
-r $REGION \
-c $CLUSTER \
-p $PROJECT
```
