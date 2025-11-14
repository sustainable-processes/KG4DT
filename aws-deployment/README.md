
# Welcome to your CDK Python project!

This is a blank project for CDK development with Python.

The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!


## KG4DT AWS CDK: DNS, Certificates, ALB routing, and Deployment

This section documents how to set up Route53, ACM, and the ALB so that:
- The public hostname `kg4dt.cdi-sg.com` lands on the FastAPI app (no path rule).
- The Knowledge Graph UI is available behind the same ALB at the path `/knowledge_graph`.
- No Cognito resources are required.

### DNS options for `kg4dt.cdi-sg.com`
There are two valid ways to host `kg4dt.cdi-sg.com`:

1) Use the parent zone `cdi-sg.com` directly (simplest)
- Keep one public hosted zone for `cdi-sg.com` in Route53.
- Create an alias `A` record named `kg4dt` pointing to the shared ALB.
- Request an ACM certificate for `kg4dt.cdi-sg.com` validated via DNS in the same `cdi-sg.com` hosted zone.

2) Create a dedicated subdomain hosted zone `kg4dt.cdi-sg.com` (delegation)
- Create a new public hosted zone in Route53 named `kg4dt.cdi-sg.com`.
- In the parent zone `cdi-sg.com` (or at your registrar), add an NS record for `kg4dt.cdi-sg.com` that lists the four Route53 nameservers from the new subdomain zone. This is required for public resolution.
- In the `kg4dt.cdi-sg.com` zone, create an alias `A` record at the zone apex (no record name) pointing to the shared ALB.
- Request an ACM certificate for `kg4dt.cdi-sg.com` and validate via DNS in the same subdomain zone.

Notes:
- Without delegation from `cdi-sg.com`, a `kg4dt.cdi-sg.com` hosted zone will not resolve publicly.
- If you use a dedicated `kg4dt.cdi-sg.com` zone, do NOT set a record name of `kg4dt` for the alias, or you would create `kg4dt.kg4dt.cdi-sg.com`. Use the apex (empty record name) instead.

### How the CDK stacks are wired
- `stacks/cluster_stack.py` creates a shared, internet-facing ALB and an HTTPS listener on 443 using your ACM certificate. The default listener action forwards to the FastAPI target group, making FastAPI the landing page.
- `stacks/workbench_stack.py` deploys the FastAPI service and registers it in the FastAPI target group. It also creates a Route53 alias `A` record so the chosen domain resolves to the ALB.
- `stacks/knowledge_graph_stack.py` deploys the GraphDB/Knowledge Graph service and attaches an ALB listener rule for the path `/knowledge_graph*` to its own target group with a health check.
- `stacks/dns_stack.py` provisions a Route53 hosted zone based on `dns_zone_name` you pass from `app.py`.
- `stacks/cert_stack.py` issues an ACM certificate for the web domain and validates via DNS in the hosted zone.

### Choosing the DNS mode in CDK
Decide which DNS option you’re using and set `dns_zone_name` accordingly in `aws-deployment/app.py`:
- Parent zone mode: `dns_zone_name = "cdi-sg.com"` and keep `A` record named `kg4dt`.
- Delegated subdomain mode: `dns_zone_name = "kg4dt.cdi-sg.com"` and make sure the alias `A` record is created at the apex (no `record_name`). If the code passes `record_name="kg4dt"`, remove it for this mode.

If you want help generating a minimal diff for switching between the two, see the guidance in the repository history or ask the maintainers.

### Building and pushing the FastAPI image
The landing page runs your FastAPI container from the ECR repo referenced as `workbench`.

1) Authenticate Docker to ECR (replace <ACCOUNT_ID> and region if different):
```
aws ecr get-login-password --region ap-southeast-1 \
  | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com
```

2) Build and tag the image using the provided Dockerfile:
```
docker build -t workbench -f ../Dockerfile-fastapi ..
```

3) Tag and push to ECR (the CDK uses `image_tag=prod`):
```
docker tag workbench:latest <ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/workbench:prod

docker push <ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/workbench:prod
```

### One-time CDK bootstrap
Ensure your local AWS CLI profile has access to the target account and region.
```
cd aws-deployment
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cdk bootstrap aws://124355682815/ap-southeast-1
```

### Deploy
1) If using delegated subdomain mode, complete DNS delegation first:
   - Create public hosted zone `kg4dt.cdi-sg.com` in Route53.
   - Copy its 4 NS servers into an NS record named `kg4dt.cdi-sg.com` inside the parent `cdi-sg.com` zone (or at the registrar).
   - Wait for propagation; validate with `dig NS kg4dt.cdi-sg.com +short`.

2) Synthesize to confirm templates:
```
cdk synth
```

3) Deploy all stacks:
```
cdk deploy --all
```
What this does:
- Looks up or creates the hosted zone as provided by `dns_zone_name`.
- Issues/validates the ACM certificate for the web domain in `ap-southeast-1`.
- Creates/updates the shared ALB and HTTPS listener (default → FastAPI TG).
- Deploys ECS services for FastAPI (root) and Knowledge Graph (path `/knowledge_graph`).
- Creates the Route53 alias record to point the public hostname to the ALB.

### Testing
- FastAPI landing page: `https://kg4dt.cdi-sg.com/` (expects 200 on `/health` for ALB health checks).
- Knowledge Graph UI: `https://kg4dt.cdi-sg.com/knowledge_graph`.

### Troubleshooting
- ACM validation stuck:
  - Ensure the DNS validation CNAMEs are present in the correct hosted zone and that subdomain delegation (if used) has propagated.
- DNS not resolving:
  - Verify NS delegation from `cdi-sg.com` to the `kg4dt.cdi-sg.com` zone (delegated mode) or confirm the `A` record `kg4dt` exists in the `cdi-sg.com` zone (parent mode).
- 5xx from ALB:
  - Confirm the FastAPI container listens on port 8000 and returns 200 at `GET /health`.
  - Check target health in the ALB console; review ECS task logs (CloudWatch) for errors.
- Wrong hostname created:
  - If your hosted zone is `kg4dt.cdi-sg.com`, ensure the alias record is at the apex (no `record_name`), not `kg4dt.kg4dt.cdi-sg.com`.

### Notes
- Cognito User Pool and domain are not required by this deployment path and were removed from the Workbench (FastAPI) service configuration.
- If you prefer a dedicated `fastapi` ECR repository instead of `workbench`, update `stacks/workbench_app_stack.py` and the image references accordingly.
