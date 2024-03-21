# Setting 1password Connect on K8s

## Naming conventions

* Vault: `<provider>-<company>-<environment>-<region>`
* Integration/Server: `<provider>-<environment>-<region>`
* Token: `<provider>-<environment>-<region>`

## Setup and Installation

* ***set up new secrets automation workflow in console***

  1. Make sure there is a 1pass vault(s) in place for your cluster/deployment. If they aren't present, create them using naming scheme:\
  `<provider>-<company>-<environment>-<region>`
     * Populate the vault using the other vaults as an example
  2. Go to this link and follow the link to the workflow setup:\
     https://developer.1password.com/docs/connect/get-started#step-1-set-up-a-secrets-automation-workflow\
     [YOU MUST APPLY ALL VAULTS AT TOKEN CREATION TIME, IF ADDING A NEW VAULT, RECREATING OR CREATING A NEW TOKEN IS A REQUIREMENT]
  3. Name the integrations as follows:\
     `<provider>-<environment>-<region>`
  4. chose the vaults relevant to the cluster/deployment
  5. save access token and 1password-credentials.json to 1password vault '1pass-connect-creds'
     * Once these are saved, go to 1pass and edit the titles to include the cluster/deployment
  6. save the 1password-credentials.json file to the location running the addon manager
  7. export the token to the env var OP_CONNECT_TOKEN:\
     `export OP_CONNECT_TOKEN=<token value>`
* ***set up new secrets automation workflow with op command line tool***

  1. Make sure there is a vault(s) in place for your cluster deployment. If not present create one with:\
  `op vault create <vault name> --allow-admins-to-manage true`\
     * vault name format should be: `<provider>-<company>-<environment>-<region>`
     * Populate the vault using the other vaults as an example
  2. Create 1pass integration with this command:\
     `op connect server create <integrations name>  --vaults <vault names>`
  3. Take note of the server UUID and the path to the 1password-crendetials.json
     * to get a current list of servers and there uuids:

      ```
      $ op connect server list
      ID                            NAME                     STATE
      Q2L7CDQWZVEBDEMAIUT2K3OQUE    aws-dev-us-west-2        ACTIVE
      63VAQGUU45DPVIFHJPMF3WAW7A    aws-prod-us-west2        ACTIVE
      FBG66EJ7RJAE7DUKWWHCABIN6I    gcp-dev-us-central1      ACTIVE
      4LDVBACBIZCEBLGD2P4I3SKE3U    gcp-prod-us-central1     ACTIVE
      52EBGJ2J5BFPDMAAP3Z5JAU7X4    gcp-prod-europe-west4    ACTIVE
      GZU72DLL3ZDIXPQYV4JXLT7ABY    aws-prod-eu-central-1    ACTIVE
      ```

  4. Create the access token for the server and store it as an env var:\
     `export OP_CONNECT_TOKEN=$(op connect token create <token name> --server <server uuid> --vault <vault names>)`
  5. Save the json credentials and the connect token to the 1pass-connect-creds vault:\
     `op item create --category 112 --title <server name>-access-token --vault 1pass-connect-creds credential=$OP_CONNECT_TOKEN`\
     `op document create  --title <server name>-credentials-file --vault 1pass-connect-creds "1password-credentials.json"`
* ***set up 1pass with existing secrets automation workflow***

  1. Go to 1password vault '1pass-connect-creds' and find the connect token and credentials json for the cluster/deployment you're working with
  2. save the 1password-credentials.json file to the location running the addon manager
  3. export the token to the env var OP_CONNECT_TOKEN:\
     `export OP_CONNECT_TOKEN=<token value>`
* ***run the addon manager targeting 1password***

  * on aws: ```addon_manager.py --config-file config.yaml aws -a create -n onepassword -r $REGION -c $CLUSTER ```
  * on gcp: ```addon_manager.py --config-file config.yaml gcp -a create -n onepassword -r $REGION -c $CLUSTER -p $PROJECT```

When setting up integrations, we will require one per cluster, as we will only be deploying the 1pass connector once per cluster. The integration should have access to all the vaults related to the applications deployed to the cluster

Integrations name format:
`<provider>-<environment>-<region>`

vault name format:
`provider-company-environment-region`

TODO:

* Update config to include version specification for secrets injector
* Make secrets injector deployment optional
* Update the json credentials file to an env variable during deployment
