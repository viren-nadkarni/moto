import boto3
import pytest

from moto import mock_aws


@mock_aws
@pytest.mark.parametrize(
    "query_string,results",
    [
        ["abc", {"abc", "abcefg", "uuuabc"}],
        ["thingName:abc", {"abc"}],
        ["thingName:ab*", {"abc", "abd", "abcefg"}],
        ["thingName:ab?", {"abc", "abd"}],
        ["*", {"abc", "abd", "bbe", "abcefg", "uuuabc", "bbefg"}],
    ],
)
def test_search_things(query_string, results):
    client = boto3.client("iot", region_name="ap-northeast-1")

    for name in ["abc", "abd", "bbe", "abcefg", "uuuabc", "bbefg"]:
        client.create_thing(thingName=name)

    resp = client.search_index(queryString=query_string)
    assert resp["thingGroups"] == []
    assert len(resp["things"]) == len(results)

    thing_names = [t["thingName"] for t in resp["things"]]
    assert set(thing_names) == results

    for thing in resp["things"]:
        del thing["connectivity"]["timestamp"]
        assert thing["connectivity"] == {"connected": True}
        assert "thingId" in thing


@mock_aws
def test_search_things_include_group_names():
    client = boto3.client("iot", region_name="ap-northeast-1")

    thing_name = "test-thing-name"
    client.create_thing(thingName=thing_name)

    client.create_thing_group(thingGroupName="TestGroup1")
    client.create_thing_group(thingGroupName="AnotherGroup")
    client.create_thing_group(thingGroupName="GroupWithoutMembers")

    client.add_thing_to_thing_group(thingName=thing_name, thingGroupName="TestGroup1")
    client.add_thing_to_thing_group(thingName=thing_name, thingGroupName="AnotherGroup")

    resp = client.search_index(queryString=f"thingName:{thing_name}")
    assert len(resp["things"]) == 1
    assert resp["things"][0]["thingGroupNames"] == ["TestGroup1", "AnotherGroup"]


@mock_aws
@pytest.mark.parametrize(
    "query_string,results",
    [["attributes.attr0:abc", {"abc"}], ["attributes.attr1:abc", set()]],
)
def test_search_attribute_specific_value(query_string, results):
    client = boto3.client("iot", region_name="ap-northeast-1")

    for idx, name in enumerate(["abc", "abd", "bbe", "abcefg", "uuuabc", "bbefg"]):
        client.create_thing(
            thingName=name, attributePayload={"attributes": {f"attr{idx}": name}}
        )

    resp = client.search_index(queryString=query_string)
    assert resp["thingGroups"] == []
    assert len(resp["things"]) == len(results)

    thing_names = [t["thingName"] for t in resp["things"]]
    assert set(thing_names) == results


@mock_aws
@pytest.mark.parametrize(
    "query_string,results",
    [
        ["thingTypeName:foo", {"foo"}],
        ["thingTypeName:nonexisting", set()],
        ["thingTypeName:b*", {"bar", "baz"}],
        ["thingTypeName:ba.", {"bar", "baz"}],
        ["thingTypeName:b.", set()],
    ],
)
def test_search_by_thing_type(query_string, results):
    client = boto3.client("iot", region_name="ap-northeast-1")

    for name in ["foo", "bar", "baz"]:
        client.create_thing_type(thingTypeName=name)
        client.create_thing(thingName=name, thingTypeName=name)

    client.create_thing(thingName="theOneWithoutThingTypeSet")

    resp = client.search_index(queryString=query_string)

    assert resp["thingGroups"] == []

    thing_names = {t["thingName"] for t in resp["things"]}
    assert thing_names == results
