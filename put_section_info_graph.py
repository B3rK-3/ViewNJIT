import json

graph = json.loads(open('graph.json').read())
sections = json.loads(open('sections.json').read())

new_graph = {}

for course_name, values in graph.items():
    course_sections = sections[course_name]
    course_title = course_sections[0]

    try:
        num_credits = float(course_sections[1][list(course_sections[1].keys())[0]][-3])
    except Exception as e:
        print(course_title)
        exit
    values['title'] = course_title
    values['credits'] = num_credits
    new_graph[course_name] = values

json.dump(new_graph, open('n_graph.json', 'w'))
