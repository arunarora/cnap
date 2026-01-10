## Kong Ingress Controller

[Kong for Kubernetes](https://github.com/Kong/kubernetes-ingress-controller)
is an open-source Ingress Controller for Kubernetes that offers
API management capabilities with a plugin architecture.

This is a meta chart that deploys an opinionated Kong Ingress Controller with
Kong Gateway using [Helm](https://helm.sh) package manager.

## Usage

```bash
helm repo add kong https://charts.konghq.com
helm repo update

helm install kong kong/ingress -n kong
```

If you need more control over what is deployed, see the [kong/kong chart](https://github.com/Kong/charts/blob/main/charts/kong/README.md). Any `values.yaml` setting can be specified in the `controller` or `gateway` section of your `values.yaml` using this chart.


*Notes*
Add Keycloak CA certificate in kong-proxy pod
----------------------------------------------
1. Find the keycloak certificate in keycloak secret secret name. You can also check your Keycloak Ingress or Deployment to see which secret holds the TLS cert.
Bash
kubectl get secret -n <cnap-namespace>
NAME                                            TYPE                 DATA   AGE
cnap-keycloak-crt                               Opaque               3      10m

2. Extract the CA (or CRT): Assuming the secret is named cnap-keycloak-crt:
Bash
kubectl get secret cnap-keycloak-crt -n <keycloak-namespace> -o jsonpath='{.data.ca\.crt}' | base64 -d > ca.crt

3. Verification
Before proceeding, verify the file is valid:
Bash
openssl x509 -in ca.crt -text -noout
If this prints certificate details (Issuer, Subject, Validity), the file is good to go.

4. Add certificate into kong-proxy
Add this to your CNAP Helm-chart values.yaml file:
YAML
kong-ingress-controller:
  enabled: true
  gateway:
    deployment:
      userDefinedVolumes:
      - name: keycloak-ca-volume
        secret:
          secretName: cnap-keycloak-crt
      userDefinedVolumeMounts:
      - name: keycloak-ca-volume
        mountPath: /etc/secrets/keycloak
        readOnly: true
    env:
      lua_ssl_trusted_certificate: "/etc/secrets/keycloak/ca.crt"