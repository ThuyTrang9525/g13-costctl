"""clean — (stretch) bulk terminate resources matching a tag.

WARNING — DESIGN-FOR-SAFETY
---------------------------
This is the most dangerous command in the CLI. Get the contract right:

  1. DEFAULT IS DRY-RUN. Without --apply the command MUST NOT touch resources.
     It only lists what WOULD be deleted.
  2. Even with --apply, you should consider printing a summary count first
     ("about to terminate N EC2 + M volumes — proceed?"), though for this
     starter a hard `--apply` flag is enough.
  3. Never use this with a tag you don't fully own. Reflection prompt in
     README covers the blast-radius scenario.

WHAT YOU MUST BUILD
-------------------
1. `_find_targets(tag_key, tag_val)` — return a dict like:
     {"ec2": [<instance ids in non-terminal state>],
      "volume": [<volume ids in 'available' state only>]}
   Skip terminated/shutting-down instances (already gone).
   Skip in-use volumes (can't delete while attached — would error anyway).

2. `run(args)` — call _find_targets, print the plan, then either:
     - bail with "(dry-run — pass --apply to ...)"  (default)
     - or actually terminate (when --apply)

HELPERS YOU CAN USE
-------------------
From commands._common:
  parse_kv(s) -> (k, v)

AWS APIS YOU'LL NEED
--------------------
- ec2.describe_instances() + describe_volumes() — same as list_cmd
- ec2.terminate_instances(InstanceIds=[...])
- ec2.delete_volume(VolumeId=...)  (per volume, no bulk API)

VERIFY
------
    pytest tests/test_clean.py -v
"""
import boto3
from botocore.exceptions import ClientError
from commands._common import parse_kv

def _find_targets(tag_key, tag_val):
    """Return {"ec2": [...], "volume": [...]} matching tag in non-terminal state."""
    ec2_client = boto3.client("ec2", region_name="us-east-1")
    targets = {"ec2": [], "volume": []}
    
    # 1. Tìm kiếm các EC2 instance phù hợp
    instances_resp = ec2_client.describe_instances()
    for reservation in instances_resp.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            state = instance["State"]["Name"]
            # Bỏ qua các instance đã hoặc đang giải thể 
            if state in ["terminated", "shutting-down"]:
                continue
            
            # Kiểm tra tag
            for tag in instance.get("Tags", []):
                if tag["Key"] == tag_key and tag["Value"] == tag_val:
                    targets["ec2"].append(instance["InstanceId"])
                    break

    # 2. Tìm kiếm các EBS Volume phù hợp
    volumes_resp = ec2_client.describe_volumes()
    for vol in volumes_resp.get("Volumes", []):
        # Đề bài yêu cầu khắt khe: CHỈ lấy các volume ở trạng thái 'available' 
        if vol["State"] != "available":
            continue
            
        # Kiểm tra tag
        for tag in vol.get("Tags", []):
            if tag["Key"] == tag_key and tag["Value"] == tag_val:
                targets["volume"].append(vol["VolumeId"])
                break
                
    return targets


def run(args):
    """Entry point.

    Args set by argparse:
        args.tag    — "key=value" string (REQUIRED)
        args.apply  — bool, must be True to actually delete (default False = dry-run)
    """
    key, val = parse_kv(args.tag)
    targets = _find_targets(key, val)
    
    total_items = len(targets["ec2"]) + len(targets["volume"])
    
    # Nếu không tìm thấy tài nguyên nào, in thông báo ra màn hình 
    if total_items == 0:
        print(f"Nothing to clean for tag {key}={val}")
        return

    ec2_client = boto3.client("ec2", region_name="us-east-1")

    # Kịch bản 1: DRY-RUN (Mặc định khi không có flag --apply) 
    if not args.apply:
        print(f"Would delete {total_items} resources matching {key}={val} (dry-run)")
        for iid in targets["ec2"]:
            print(f"Would terminate ec2 instance: {iid}")
        for vid in targets["volume"]:
            print(f"Would delete volume: {vid}")
    
    # Kịch bản 2: Thực hiện xóa thực tế khi truyền flag --apply 
    else:
        # Tiến hành hủy bỏ các EC2 instance tìm được 
        if targets["ec2"]:
            try:
                ec2_client.terminate_instances(InstanceIds=targets["ec2"])
                for iid in targets["ec2"]:
                    print(f"Terminated ec2 instance: {iid}")
            except ClientError as e:
                print(f"Error terminating instances: {e}")
                
        # Tiến hành xóa các EBS Volume độc lập 
        for vid in targets["volume"]:
            try:
                ec2_client.delete_volume(VolumeId=vid)
                print(f"Deleted volume: {vid}")
            except ClientError as e:
                print(f"Error deleting volume {vid}: {e}")