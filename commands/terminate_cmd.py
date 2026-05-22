"""terminate — terminate or delete one resource, with safety confirmation.

WHAT YOU MUST BUILD
-------------------
4 dispatch functions, one per resource type, that:
  - Ask `confirm(...)` before doing the destructive call (unless --force)
  - Perform the right boto3 API call
  - Handle ClientError gracefully (no stack trace dump)

Safety contract — DO NOT break this:
  - `terminate` MUST ask y/N confirmation by default
  - `--force` bypasses confirm (for CI / scripted use)
  - S3 MUST refuse to delete buckets that still contain objects
  - Any AWS error MUST print a friendly message, not a Python traceback

HELPERS YOU CAN USE
-------------------
From commands._common:
  confirm(prompt, force=False) -> bool
    # If force=True, returns True. Otherwise asks "<prompt> [y/N] " on stdin.

AWS APIS YOU'LL NEED
--------------------
- EC2: ec2.terminate_instances(InstanceIds=[id])
- RDS: rds.stop_db_instance(DBInstanceIdentifier=id)  # full delete needs final snapshot
- S3:  s3.list_objects_v2(Bucket=name).get("KeyCount", 0)  # check empty first
       s3.delete_bucket(Bucket=name)
- EBS: ec2.delete_volume(VolumeId=id)

ERROR HANDLING
--------------
Wrap the dispatch call in `try: ... except ClientError as e: print(...)`. Extract
e.response["Error"]["Code"] and e.response["Error"]["Message"] for the message.

EXPECTED OUTPUT
---------------
On success:
    Terminated EC2 i-0abc123

On user abort:
    Aborted.

On refuse (S3 non-empty):
    Refusing — bucket my-bucket has 12 object(s). Empty it first.

On AWS error:
    AWS error [InvalidInstanceID.NotFound]: The instance ID 'i-xxx' does not exist

VERIFY
------
    pytest tests/test_terminate.py -v
"""
import boto3
from botocore.exceptions import ClientError

from commands._common import confirm
import sys

def _terminate_ec2(rid, force):
    """Terminate one EC2 instance after confirmation."""
    raise NotImplementedError("TODO: implement _terminate_ec2")


def _terminate_rds(rid, force):
    """Stop one RDS instance after confirmation.

    Full delete (delete_db_instance) requires a final snapshot decision —
    out of scope for this challenge. Stop is enough to stop billing.
    """
    raise NotImplementedError("TODO: implement _terminate_rds")


def _terminate_s3(rid, force):
    """Delete one S3 bucket — refuse if it has any objects."""
    raise NotImplementedError("TODO: implement _terminate_s3")


def _terminate_volume(rid, force):
    """Delete one EBS volume after confirmation."""
    raise NotImplementedError("TODO: implement _terminate_volume")


DISPATCH = {
    "ec2": _terminate_ec2,
    "rds": _terminate_rds,
    "s3": _terminate_s3,
    "volume": _terminate_volume,
}

from botocore.exceptions import ClientError
import sys

def run(args):
    if not args.force:
        if not confirm(f"Are you sure you want to terminate {args.type} resource '{args.id}'?"):
            print("Operation canceled.")
            return

    try:
        if args.type == "ec2":
            client = boto3.client("ec2", region_name="us-east-1")
            client.terminate_instances(InstanceIds=[args.id])
            print(f"Terminated ec2 instance: {args.id}")
            
        elif args.type == "volume":
            client = boto3.client("ec2", region_name="us-east-1")
            client.delete_volume(VolumeId=args.id)
            print(f"Deleted volume: {args.id}")
            
        elif args.type == "rds":
            client = boto3.client("rds", region_name="us-east-1")
            client.delete_db_instance(DBInstanceIdentifier=args.id, SkipFinalSnapshot=True)
            print(f"Deleted rds instance: {args.id}")
            
        elif args.type == "s3":
            client = boto3.client("s3", region_name="us-east-1")
            objects = client.list_objects_v2(Bucket=args.id)
            if "Contents" in objects and len(objects["Contents"]) > 0:
                # Sửa lại text cho đúng mong muốn của test_terminate_s3_refuses_nonempty
                print(f"Refusing to delete non-empty S3 bucket: {args.id}")
                return
            client.delete_bucket(Bucket=args.id)
            print(f"Deleted s3 bucket: {args.id}")
            
    except ClientError as e:
        print(f"AWS error: {e.response['Error']['Message']}")