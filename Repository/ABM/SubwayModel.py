from ABM.SubwayAgent import SubwayAgent
from mesa.time import RandomActivation
from ABM.SubwayGraph import SubwayGraph
from Parameters import AgentParams, EnvParams
import networkx as nx
from ABM.TransportationModel import TransportationModel


class SubwayModel(TransportationModel):
    """This guy's constructor should probably have a few more params."""
    def __init__(self, subway_map, routing_dict):
        self._subway_graph = SubwayGraph(subway_map, routing_dict)
        self._agent_loc_dictionary = {}  # a dictionary of locations with lists of agents at each location
        self._zip_to_station_dictionary = {}
        self.countermeasures = {}
        self.schedule = RandomActivation(self)
        # Create agents
        agent_id = 0
        for loc in list(self.subway_graph.graph.nodes()):
            # Add Agents
            agent_id += 1  # we will keep agent ids different from location for now.
            population = subway_map.nodes[loc]['population']
            a = SubwayAgent(agent_id, self, loc, population)
            if loc == AgentParams.MAP_LOCATION_JUNCTION_BLVD \
                    or loc == AgentParams.MAP_LOCATION_55_ST \
                    or loc == AgentParams.MAP_LOCATION_98_BEACH:  # TODO: this method of seeding is actually quite bad.
                a.population[AgentParams.STATUS_EXPOSED] += population * 0.5 * 2.5e-6
                a.population[AgentParams.STATUS_INFECTED] += population * 0.5 * 1.0e-6
                a.population[AgentParams.STATUS_RECOVERED] += 0
                a.population[AgentParams.STATUS_SUSCEPTIBLE] -= population * 0.5 * 3.5e-6

            elif loc == AgentParams.MAP_LOCATION_COLMENAR_VIEJO:
                a.population[AgentParams.STATUS_EXPOSED] += population * 0.00025
                a.population[AgentParams.STATUS_INFECTED] += population * 0.00010
                a.population[AgentParams.STATUS_RECOVERED] += 0
                a.population[AgentParams.STATUS_SUSCEPTIBLE] -= population * 0.00035

            else:
                a.population[AgentParams.STATUS_EXPOSED] += population * 0.1 * 2.5e-6
                a.population[AgentParams.STATUS_INFECTED] += population * 0.1 * 1.0e-6
                a.population[AgentParams.STATUS_RECOVERED] += 0
                a.population[AgentParams.STATUS_SUSCEPTIBLE] -= population * 0.1 * 3.5e-6


            self.schedule.add(a)

            # Fill Zip-to-station dictionary
            station_zip = subway_map.nodes[loc]['zip']
            self.zip_to_station_dictionary.setdefault(station_zip, []).append(loc)


    # Decay the viral loads in the environment. just wipes them for now.
    def decay_viral_loads(self):
        for a in self.schedule.agents:
            self.subway_graph.graph.nodes[a.location]['infected'] = a.population[AgentParams.STATUS_INFECTED]
        nx.set_node_attributes(self.subway_graph.graph, 0, 'viral_load')
        return None

    def increment_viral_loads(self):
        for a in self.schedule.agents:
            a.infect()  # Really, the model could do all this itself, but calling agents keeps with ABM philosophy
        return None

    def step(self):
        self.decay_viral_loads() #TODO: yes, this belongs at the end of a step. but i need my snapshot to be mid-day
        self.increment_viral_loads()
        self.schedule.step()
        self.subway_graph.update_hotspots(self.schedule.agents) #TODO: repair this later
        self.update_countermeasures()

    def update_countermeasures(self):
        active = self.countermeasures
        infected = 0
        for a in self.schedule.agents:
            infected += a.population[AgentParams.STATUS_INFECTED]
        if EnvParams.ISOLATION_COUNTERMEASURE not in active.keys():
            if infected >= 3000:
                active[EnvParams.ISOLATION_COUNTERMEASURE] = self.schedule.time
                print('isolation countermeasure taken!')
        # if EnvParams.RECOMMENDATION_COUNTERMEASURE not in active.keys():
        #     if infected >= 500:
        #         active[EnvParams.RECOMMENDATION_COUNTERMEASURE] = self.schedule.time
        #         print('recommendation countermeasure taken!')
        # if EnvParams.AWARENESS_COUNTERMEASURE not in active.keys():
        #     if infected >= 500:  # start awareness campaign
        #         active[EnvParams.AWARENESS_COUNTERMEASURE] = self.schedule.time
        #         print('awareness countermeasure taken!')

    def calculate_SEIR(self, print_results=False):
        sick, exposed, infected, recovered = 0, 0, 0, 0
        for a in self.schedule.agents:
            sick += a.population[AgentParams.STATUS_SUSCEPTIBLE]
            exposed += a.population[AgentParams.STATUS_EXPOSED]
            infected += a.population[AgentParams.STATUS_INFECTED]
            recovered += a.population[AgentParams.STATUS_RECOVERED]
        if print_results:
            print('S,E,I,R:', sick, exposed, infected, recovered)
        return [sick, exposed, infected, recovered]


    def calculate_modzcta_case_rate(self, case_rates_dict, iteration):
        #for now this calculates cumulative case rate by modzcta and returns a dictionary of those values
        #TODO: per usual we're totally ignoring that multiple stations are in one zip.
        for a in self.schedule.agents:
            loc = a.location
            loc_case_rate = a.population[AgentParams.STATUS_INFECTED] + a.population[AgentParams.STATUS_RECOVERED]
            loc_case_rate /= sum(a.population.values())
            station_zip = self.subway_graph.graph.nodes[loc]['zip']
            #on iteration 1, it is ok to add if <= 1 entries
            if station_zip in case_rates_dict.keys():
                if len(case_rates_dict[station_zip]) <= iteration:
                    case_rates_dict[station_zip].append(loc_case_rate)
            else:
                case_rates_dict[station_zip] = [loc_case_rate]
        return case_rates_dict

    @property
    def subway_graph(self):
        return self._subway_graph

    @subway_graph.setter
    def subway_graph(self, value):
        self._subway_graph = value

    # TODO: I think this might actually be better at the graph level.
    @property
    def zip_to_station_dictionary(self):
        return self._zip_to_station_dictionary

    @zip_to_station_dictionary.setter
    def zip_to_station_dictionary(self, value):
        self._zip_to_station_dictionary = value

