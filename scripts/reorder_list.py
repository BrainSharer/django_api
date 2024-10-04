def resort_points(rows):
    """Reorders a list of dictionaries based on the previous value of a specified key."""


    result = [rows[0]]  # Start with the first dictionary
    for i in range(1, len(rows)):
        for j in range(i):
            if rows[i]['pointA'] == result[j]['pointB']:
                result.insert(j + 1, rows[i])
                break
        else:
            result.append(rows[i])

    return result

    
rows = [
    {
        "pointA": [22436.53125, 27149.595703125, 54.5],
        "pointB": [23024.7578125, 26826.513671875, 54.5],
    },
    {
        "pointA": [14138.087890625, 25630.14453125, 54.5],
        "pointB": [14535.1533203125, 26375.423828125, 54.5],
    },
    {
        "pointA": [14535.1533203125, 26375.423828125, 54.5],
        "pointB": [15421.7158203125, 28767.080078125, 54.5],
    },
    {
        "pointA": [15421.7158203125, 28767.080078125, 54.5],
        "pointB": [14865.037109375, 30767, 54.5],
    },
    {
        "pointA": [14865.037109375, 30767, 54.5],
        "pointB": [13957.857421875, 33529.77734375, 54.5],
    },
    {
        "pointA": [13957.857421875, 33529.77734375, 54.5],
        "pointB": [13504.2666015625, 35529.6953125, 54.5],
    },
    {
        "pointA": [13504.2666015625, 35529.6953125, 54.5],
        "pointB": [18266.962890625, 36230.69921875, 54.5],
    },
    {
        "pointA": [18266.962890625, 36230.69921875, 54.5],
        "pointB": [19545.26171875, 30457.734375, 54.5],
    },
    {
        "pointA": [19545.26171875, 30457.734375, 54.5],
        "pointB": [19833.91015625, 29488.701171875, 54.5],
    },
    {
        "pointA": [19833.91015625, 29488.701171875, 54.5],
        "pointB": [20081.322265625, 28973.2578125, 54.5],
    },
    {
        "pointA": [20081.322265625, 28973.2578125, 54.5],
        "pointB": [20947.267578125, 28725.845703125, 54.5],
    },
    {
        "pointA": [20947.267578125, 28725.845703125, 54.5],
        "pointB": [21591.125, 27866.97265625, 54.5],
    },
    {
        "pointA": [21591.125, 27866.97265625, 54.5],
        "pointB": [22436.53125, 27149.595703125, 54.5],
    },
    {
        "pointA": [23024.7578125, 26826.513671875, 54.5],
        "pointB": [14138.087890625, 25630.14453125, 54.5],
    },
]
first = [round(x) for x in rows[0]['pointA']]
last = [round(x) for x in rows[-1]['pointB']] 
print()
print(f'Unsorted firstA={first} lastB={last} len points={len(rows)} first = last {first == last}')
for i, row in enumerate(rows):
    currentA = [round(x) for x in rows[i]['pointA']]
    currentB = [round(x) for x in rows[i]['pointB']]
    beforeB = [round(x) for x in rows[i-1]['pointB']]
    print(f"pointA{i}={currentA} pointB{i}={currentB} pointB{i-1}={beforeB} currentA = beforeB {currentA == beforeB}')")

rows = resort_points(rows)

first = [round(x) for x in rows[0]['pointA']]
last = [round(x) for x in rows[-1]['pointB']] 
print()
print(f'Sorted firstA={first} lastB={last} len points={len(rows)} first = last {first == last}')
for i, row in enumerate(rows):
    currentA = [round(x) for x in rows[i]['pointA']]
    currentB = [round(x) for x in rows[i]['pointB']]
    beforeB = [round(x) for x in rows[i-1]['pointB']]
    print(f"pointA{i}={currentA} pointB{i}={currentB} pointB{i-1}={beforeB} currentA = beforeB {currentA == beforeB}')")
