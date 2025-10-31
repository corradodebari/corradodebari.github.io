## Oracle Backend for Microservices and AI (rel. 1.4.0)

To simplify as much as possible the process, configure the Oracle Backend for Microservices and AI Autonomous DB to run the AI Optimizer and toolkit. In this way, you can get smoothly the vectorstore created to be copied as a dedicated version for the microservice running. If you prefer to run the microservice in another user schema, before the step **5.** execute the steps described at  **Other deployment options** chapter.

![obaas](images/obass_cover.jpg)

* Create a user/schema via oractl. First open a tunnel:
```
kubectl -n obaas-admin port-forward svc/obaas-admin 8080:8080
```

* run `oractl` and connect with the provided credentials

* create a namespace to host the AI Optimizer and Toolkit :

```
namespace create --namespace <OPTIMIZER_NAMESPACE>
```

* create the datastore, saving the passoword provided:
```
datastore create --namespace <OPTIMIZER_NAMESPACE> --username <OPTIMIZER_USER> --id <DATASTORE_ID>
```

* For the AI Optimizer and Toolkit local startup,  setting this env variables in startup:

```
DB_USERNAME=<OPTIMIZER_USER>
DB_PASSWORD=<OPTIMIZER_USER_PASSWORD>
DB_DSN="<Connection_String_to_Instance>"
DB_WALLET_PASSWORD=<Wallet_Password>
TNS_ADMIN=<Wallet_Zip_Full_Path>
```

NOTE: if you need to access to the Autonomus Database backing the platform as admin, execute:
```
kubectl -n application get secret <DB_NAME>-db-secrets -o jsonpath='{.data.db\.password}' | base64 -d; echo
```
to do, for example:
```
DROP USER vectorusr CASCADE;
```

Then proceed as described in following steps:

1. Create an `ollama-values.yaml` to be used with **helm** to provision an Ollama server. This step requires you have a GPU node pool provisioned with the Oracle Backend for Microservices and AI. Include in the models list to pull the model used in your Spring Boot microservice. Example:

```
ollama:
  gpu:
    enabled: true
    type: 'nvidia'
    number: 1
  models:
    pull:
      - llama3.1
      - llama3.2
      - mxbai-embed-large
      - nomic-embed-text
nodeSelector:
  node.kubernetes.io/instance-type: VM.GPU.A10.1
```

2. Execute the helm chart provisioning:

```
helm upgrade --install ollama ollama-helm/ollama \
  --namespace ollama \
  --create-namespace \
  --values ollama-values.yaml
```

Check if the deployment is working at the end of process.
You should get this kind of output:

```
1. Get the application URL by running these commands:
  export POD_NAME=$(kubectl get pods --namespace ollama -l "app.kubernetes.io/name=ollama,app.kubernetes.io/instance=ollama" -o jsonpath="{.items[0].metadata.name}")
  export CONTAINER_PORT=$(kubectl get pod --namespace ollama $POD_NAME -o jsonpath="{.spec.containers[0].ports[0].containerPort}")
  echo "Visit http://127.0.0.1:8080 to use your application"
  kubectl --namespace ollama port-forward $POD_NAME 8080:$CONTAINER_PORT
```

3. check all:
* run: 
```
kubectl -n ollama exec svc/ollama -- ollama ls
```
it should be:
```
NAME                        ID              SIZE      MODIFIED      
nomic-embed-text:latest     0a109f422b47    274 MB    3 minutes ago    
mxbai-embed-large:latest    468836162de7    669 MB    3 minutes ago    
llama3.1:latest             a80c4f17acd5    2.0 GB    3 minutes ago 
```
* test a single LLM:
```
kubectl -n ollama exec svc/ollama -- ollama run "llama3.1" "what is spring boot?"
```

NOTICE: for network issue related to huge model download, the process could stuck. Repeat it, or choose to pull manually just for test, removing from the helm chart the `models` part in `ollama-values.yaml`. 

To remove it and repeat:
* get the ollama <POD_ID> stuck:
```
kubectl get pods -n ollama
```
* the uninstall:
```
helm uninstall ollama --namespace ollama

kubectl delete pod <POD_ID> -n ollama --grace-period=0 --force
kubectl delete pod -n ollama --all --grace-period=0 --force
kubectl delete namespace ollama
```
* install helm chart without models
* connect to the pod to pull manually:
```
kubectl exec -it <POD_ID> -n ollama -- bash
```
* run: 
```
ollama pull llama3.2
ollama pull mxbai-embed-large
```

* Build, depending the provider `<ollama|openai>`:

```
mvn clean package -DskipTests -P <ollama|openai> -Dspring-boot.run.profiles=obaas
```

4. Connect via oractl to deploy the microservice, if not yet done:

* First open a tunnel:
```
kubectl -n obaas-admin port-forward svc/obaas-admin 8080:8080
```
* run `oractl` and connect with the provided credentials

5. Execute the deployment:

```
artifact create --namespace <OPTIMIZER_NAMESPACE>  --workload <WORKLOAD_NAME> --imageVersion 0.0.1 --file <FULL_PATH_TO_JAR_FILE>

image create --namespace <OPTIMIZER_NAMESPACE>  --workload <WORKLOAD_NAME>--imageVersion 0.0.1

workload create --namespace <OPTIMIZER_NAMESPACE>  --imageVersion 0.0.1 --id <WORKLOAD_NAME> --cpuRequest 100m --framework SPRING_BOOT

binding create --namespace <OPTIMIZER_NAMESPACE>  --datastore <DATASTORE_ID> --workload <WORKLOAD_NAME> --framework SPRING_BOOT
```

6. Let's test:
* open a tunnel:

```
kubectl -n <OPTIMIZER_NAMESPACE> port-forward svc/<WORKLOAD_NAME> 9090:8080
```

* test via curl. Example:

```
curl -N http://localhost:9090/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key" \
  -d '{
    "model": "server",
    "messages": [{"role": "user", "content": "Can I use any kind of development environment to run the example?"}],
    "stream": false
  }'
```

7. Open to external access via APISIX Gateway:

* get the Kubernetes <EXTERNAL-IP> address:

```
kubectl -n ingress-nginx get svc ingress-nginx-controller
```

* get the APISIX password:

```
kubectl get secret -n apisix apisix-dashboard -o jsonpath='{.data.conf\.yaml}' | base64 -d | grep 'password:'; echo
```
* connect to APISIX console:
```
kubectl port-forward -n apisix svc/apisix-dashboard 8090:80
```
and provide the credentials at local url http://localhost:8090/,  `admin`/<PWD>

* Create a route to access the microservice:

```
Name: <WORKLOAD_NAME>
Path: /v1/chat/completions*
Algorithm: Round Robin
Upstream Type: Node
Targets: 
  Host:<WORKLOAD_NAME>.<OPTIMIZER_NAMESPACE>.svc.cluster.local
  Port: 8080
```

8. Test the access to the public IP. Example:
```
curl -N http://<EXTERNAL-IP>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key" \
  -d '{
    "model": "server",
    "messages": [{"role": "user", "content": "Can I use any kind of development environment to run the example?"}],
    "stream": false
  }'
```



### Other deployment options

If you want to run on another schema instead the <OPTIMIZER_USER>, you should add a few steps.

1. Connect to the backend via oractl:

* First open a tunnel:
```
kubectl -n obaas-admin port-forward svc/obaas-admin 8080:8080
```
* Run `oractl` and connect with the provided credentials

* Create a dedicated namespace for the microservice:

```
namespace create --namespace <MS_NAMESPACE>
```

* Create a dedicated user/schema for the microservice, providing a <MS_USER_PWD> to execute the command:

```
datastore create --namespace <MS_NAMESPACE> --username <MS_USER> --id <MS_DATASTORE_ID>
```


2. Connect to the Autonomous DB instance via the <OPTIMIZER_USER>/<OPTIMIZER_USER_PASSWORD>

* Grant access to the microservice user to copy the vectorstore used:

```
GRANT SELECT ON "<OPTIMIZER_USER>"."<VECTOR_STORE_TABLE>" TO <MS_USER>;
```

3. Then proceed from the step 5. as usual, changing:

<OPTIMIZER_USER> -> <MS_USER>
<OPTIMIZER_NAMESPACE> -> <MS_NAMESPACE>
<DATASTORE_ID> -> <MS_DATASTORE_ID>


### Cleanup env

* First open a tunnel:
```
kubectl -n obaas-admin port-forward svc/obaas-admin 8080:8080
```

* Run `oractl` and connect with the provided credentials:

```
workload list --namespace <MS_NAMESPACE>
workload delete --namespace <MS_NAMESPACE> --id myspringai
image list
image delete --imageId <ID_GOT_WITH_IMAGE_LIST>
artifact list
artifact delete --artifactId <ID_GOT_WITH_ARTIFACT_LIST>
```
* disconnect <OPTIMIZER_USER> from  DB (the Optimizer server) and finally:


```
#CLOSE Optimizer befor delete
datastore delete --namespace <OPTIMIZER_NAMESPACE> --id optimizerds
namespace delete optimizerns

```

## Conclusion
Hoping this article has made you want to try Spring AI Optimizer outcome on Oracle Backend for Microservices and AI, see you for the next in-depth articles on the topic.

---

## Disclaimer
*The views expressed in this paper are my own and do not necessarily reflect the views of Oracle.*

