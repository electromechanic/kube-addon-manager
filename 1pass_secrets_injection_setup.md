# Enabling Secrets Injection in K8s Applications

1. create 1password connect token secret in the namespace of the app you are injecting secrets to. Token can be found in vault "1pass-connect-creds". Export the token to your local env then add it as a secret. (In the case of a new token, token must be created in the 1pass console for the target vault)
`kubectl -n <your-namespace> create secret generic connect-token --from-literal=token=$OP_CONNECT_TOKEN`

2. Enable secrets injection in the namespace
`kubectl label namespace <your-namespace> secrets-injection=enabled`

3. add an annotation in the template metadata for your spec to specify what containers you want to inject secrets"
```
spec:
  template:
    metadata:
      annotations:
        operator.1password.io/inject: "<my-application>" 
```

4. include the url to the connect host, and a reference to the connect token secret to the environment vars of your container spec
```
spec:
  template:
    spec:
      containers:
      - name: nginx
        image: nginx:1.14.2
        command:  ["nginx", "-g", "daemon off;"]
        env:
        - name: OP_CONNECT_HOST
          value: http://onepassword-connect.onepassword.svc.cluster.local:8080
        - name: OP_CONNECT_TOKEN
          valueFrom:
            secretKeyRef:
              name: connect-token
              key: token
```

5. add your secrets as environment variables with op:// urls
  ```
  spec:
    template:
      spec:
        containers:
        - name: nginx
          image: nginx:1.14.2
          command:  ["nginx", "-g", "daemon off;"]
          env:
          - name: DB_USERNAME
            value: op://vault-dev-gcp/sisu-aurora-password/password
  ```

[NOTE: IT IS REQUIRED THAT THE CONTAINER SPEC CONTAINS A "command:" ARGUMENT]
