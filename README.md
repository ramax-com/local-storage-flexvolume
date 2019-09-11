# local-storage-flexvolume

Create storage directory on K8S node and set UID/GID/mode for mounting into non-root container.

    - name: VOLUME-NAME
      flexVolume:
        driver: ramax.com/local-storage
        options:
          volume-mode: "33"
          volume-gid: "33"
          volume-mode: "0750"

The driver will allocate a directory on a server with path /srv/NAMESPACE/VOLUME-NAME.

Please note that since flexvolume does not provide node affinity
support, you must explicitly bind your workload to a node using
nodeSelector. See https://kubernetes.io/docs/concepts/configuration/assign-pod-node/


## Deploy flexvolume driver to the cluster:

    kubectl create -n kube-system cm flexvolume-drivers --from-file=local-storage=local-storage-driver.py
    kubectl apply -n kube-system -f deploy-flexvolume-drivers.yaml


## Test volume creation:

    kubectl apply -f test-pod.yaml

    kubectl exec test-flexvolume -- ls -l /data
    