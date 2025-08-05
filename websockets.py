import json
import boto3

def websocket_handler(event, context):
    if "requestContext" not in event:
        print(f"Malformed event, missing requestContext: {json.dumps(event)}")
        return {"statusCode": 400, "body": "Bad event structure: missing requestContext."}

    route_key = event["requestContext"]["routeKey"]
    connection_id = event["requestContext"]["connectionId"]
    domain_name = event["requestContext"]["domainName"]
    stage = event["requestContext"]["stage"]

    print(f"connection id: {connection_id}\n route key: {route_key}")

    apigw_client = boto3.client(
        "apigatewaymanagementapi",
        endpoint_url=f"https://{domain_name}/{stage}"
    )

    if route_key == "$connect":
        print(f"New connection: {connection_id}")
        return {"statusCode": 200}

    elif route_key == "$disconnect":
        print(f"Disconnected: {connection_id}")

        try:
            apigw_client.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps({
                    "message": "Remove from Database",
                    "connection_id": connection_id
                }).encode("utf-8")
            )

        except apigw_client.exceptions.GoneException:
            print(f"Connection {connection_id} is gone")
        except Exception as e:
            print(f"Error sending message: {e}")
        return {"statusCode": 200}

    elif route_key == "$default":
        try:
            body = json.loads(event.get("body", "{}"))
        except json.JSONDecodeError:
            body = {}
        return {"statusCode": 200}

    elif route_key == "register_device":
        try:
            body = json.loads(event.get("body", "{}"))
        except json.JSONDecodeError:
            body = {}

        if body.get("message") == "Connection Established":
            try:
                apigw_client.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps({
                        "message": "Save to Database",
                        "connection_id": connection_id
                    }).encode("utf-8")
                )

            except apigw_client.exceptions.GoneException:
                print(f"Connection {connection_id} is gone")
            except Exception as e:
                print(f"Error sending message: {e}")
        return {"statusCode": 200}

    else:
        print(f"Unhandled route: {route_key}")
        return {"statusCode": 200}