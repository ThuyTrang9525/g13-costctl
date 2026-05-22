"""list — list AWS resources by type, filter by tag / missing-tag.

WHAT YOU MUST BUILD
-------------------
Support 4 resource types: ec2, rds, s3, volume.
Each takes:
- `want` — list of (key, value) tag pairs the resource MUST have
- `missing` — list of tag keys the resource MUST NOT have

Print a formatted table to stdout. Test cases are in tests/test_list.py.

HELPERS YOU CAN USE
-------------------
From commands._common:
  parse_kv(s) -> (k, v)            # "Owner=alice" -> ("Owner", "alice")
  tags_to_dict(items) -> dict       # boto3 [{"Key","Value"}] -> {k: v}
  tags_match(tags, want, missing) -> bool

AWS APIS YOU'LL NEED
--------------------
- EC2: ec2.describe_instances() with get_paginator
- RDS: rds.describe_db_instances(), then list_tags_for_resource(ResourceName=arn)
- S3:  s3.list_buckets(), then get_bucket_tagging(Bucket=name)
       (catch ClientError when bucket has no tagging config — treat as {})
- EBS: ec2.describe_volumes() with get_paginator

EXPECTED OUTPUT FORMAT (when run from CLI)
------------------------------------------
    EC2 Environment=dev — 1 found:
    ------------------------------------------------------------------------------
      i-0abc123def456789a       t3.micro       running       Environment=dev

VERIFY
------
    pytest tests/test_list.py -v
"""
import boto3

from commands._common import parse_kv, tags_to_dict, tags_match


def _list_ec2(want, missing):
    client = boto3.client("ec2", region_name="us-east-1")
    response = client.describe_instances()
    rows = []
    for reservation in response.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            instance_id = instance["InstanceId"]
            instance_type = instance["InstanceType"]
            state = instance["State"]["Name"]
            
            # Chuyển đổi định dạng tag AWS sang dict
            tags_dict = {t["Key"]: t["Value"] for t in instance.get("Tags", [])}
            
            # Sử dụng helper tags_match để lọc tài nguyên
            if tags_match(tags_dict, want, missing):
                rows.append((instance_id, instance_type, state, tags_dict))
    return rows

def _list_rds(want, missing):
    """Same shape as _list_ec2 but for RDS DB instances.

    Note: RDS tags require a separate API call per DB:
        rds.list_tags_for_resource(ResourceName=db['DBInstanceArn'])

    Returns:
        list of (db_id, db_class, db_status, tags_dict) tuples
    """
    raise NotImplementedError("TODO: implement _list_rds")


from botocore.exceptions import ClientError

def _list_s3(want, missing):
    client = boto3.client("s3", region_name="us-east-1")
    response = client.list_buckets()
    rows = []
    for bucket in response.get("Buckets", []):
        name = bucket["Name"]
        tags_dict = {}
        try:
            tagging = client.get_bucket_tagging(Bucket=name)
            tags_dict = {t["Key"]: t["Value"] for t in tagging.get("TagSet", [])}
        except ClientError as e:
            # Nếu bucket không có tag, AWS sẽ báo lỗi ClientError. Ta coi như tag rỗng.
            if e.response["Error"]["Code"] == "NoSuchTagSet":
                tags_dict = {}
            else:
                raise e
        
        if tags_match(tags_dict, want, missing):
            rows.append((name, "bucket", "active", tags_dict))
    return rows

def _list_volume(want, missing):
    client = boto3.client("ec2", region_name="us-east-1")
    response = client.describe_volumes()
    rows = []
    for vol in response.get("Volumes", []):
        volume_id = vol["VolumeId"]
        vol_type = vol["VolumeType"]
        size = vol["Size"]
        type_str = f"{vol_type}-{size}GB"
        state = vol["State"]
        
        tags_dict = {t["Key"]: t["Value"] for t in vol.get("Tags", [])}
        
        if tags_match(tags_dict, want, missing):
            rows.append((volume_id, type_str, state, tags_dict))
    return rows

DISPATCH = {
    "ec2": _list_ec2,
    "rds": _list_rds,
    "s3": _list_s3,
    "volume": _list_volume,
}

def run(args):
    """Entry point.

    Args set by argparse:
        args.resource      — "ec2", "rds", "s3", "volume", or "all"
        args.tag           — "key=value" filter string (optional)
        args.missing_tag   — key string that must NOT be present (optional)
    """
    from commands._common import parse_kv

    # Phân tách bộ lọc tag nếu người dùng nhập vào
    want = [parse_kv(args.tag)] if args.tag else []
    missing = [args.missing_tag] if args.missing_tag else []

    # Cơ chế phòng vệ an toàn: Kiểm tra xem argparse đang dùng biến 'resource' hay 'type'
    res_attr = "resource" if hasattr(args, "resource") else "type"
    chosen_resource = getattr(args, res_attr)

    # Xác định danh sách các tài nguyên cần quét dựa theo tham số
    target_resources = ["ec2", "volume", "rds", "s3"] if chosen_resource == "all" else [chosen_resource]

    # Bản đồ ánh xạ gọi đến các hàm xử lý dữ liệu tương ứng của từng dịch vụ
    dispatch = {
        "ec2": _list_ec2,
        "volume": _list_volume,
        "rds": _list_rds,
        "s3": _list_s3
    }

    # Tiến hành duyệt qua và in kết quả ra màn hình terminal
    for res_type in target_resources:
        if res_type in dispatch:
            rows = dispatch[res_type](want, missing)
            
            # Khai báo tiêu đề hiển thị cho từng nhóm tài nguyên
            filter_info = f" (filter: {args.tag})" if args.tag else (f" missing:{args.missing_tag}" if args.missing_tag else " (no filter)")
            print(f"{res_type.upper()}{filter_info} — {len(rows)} found:")
            print("-" * 78)
            
            # In chi tiết từng tài nguyên gặt hái được
            for row in rows:
                res_id, r_type, state, tags = row
                tags_str = " ".join([f"{k}={v}" for k, v in tags.items()]) if tags else "(no tags)"
                print(f"  {res_id:<25} {r_type:<14} {state:<13} {tags_str}")
            print()