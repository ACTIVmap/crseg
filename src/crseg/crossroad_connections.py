
class CrossroadConnections:

    typology_crossroad = 1
    typology_link = 2
    typology_unknown = 0

    # the connection_threshold corresponds to a coefficient used for connection
    # between crossroads, multiplied by an estimation of the size of a crossroad
    # defined by an estimation of the branch width
    def __init__(self, regions, connection_threshold = 2):
        self.regions = regions
        self.connection_threshold = connection_threshold

        self.init_structure()

    def init_structure(self):

        # build the list of crossroad and links
        self.crossroads = []
        self.links = []

        for rid in self.regions:
            if self.regions[rid].is_crossroad():
                self.crossroads.append(rid)
            elif self.regions[rid].is_link():
                self.links.append(rid)

        # for each node, build the list of intersecting regions
        self.regionsByNode = {}
        for rid in self.regions:
            for n in self.regions[rid].nodes:
                self.add_node_region(rid, n)

        # for each region, the list of its adjacent regions (only links for crossroads, and only crossroads for links)
        self.adjacencies = {}
        # for each junction node
        for n in self.regionsByNode:
            # for reach region associated to this node
            for r1 in self.regionsByNode[n]:
                # add an adjacency between this region and all regions connected via the current node
                self.add_adjacencies(r1, n, self.regionsByNode[n])

        # compute a list of connections between crossroads
        self.compute_connected_crossroads()

    def compute_connected_crossroads(self):
        self.compute_initial_connections()

        merged = {}
        

        # merge multiple instances of the same pair of connected crossroads
        for c in self.connected_crossroads:
            if (c[0], c[1]) in merged:
                merged[(c[0], c[1])].append(c[2])
            else:
                merged[(c[0], c[1])] = [c[2]]
        
        new_list = []
        for c in merged:
            new_list.append((c[0], c[1], merged[c]))
        
        self.connected_crossroads = new_list

    def compute_initial_connections(self):
        self.connected_crossroads = []
        # for each crossroad region
        for cr in self.crossroads:
            # for each adjacent links
            for l in self.adjacencies[cr]:
                # then find the reachable crossings from this link
                for cr2 in self.adjacencies[l]:
                    # only considering the ones with an ID higher to the ID of the initial crossroad region
                    if self.regions[cr].id < self.regions[cr2].id:
                        path, distance = self.get_path_in_link(l, cr, cr2)
                        # add them as a pair with the corresponding path only if the path is not too long
                        if distance < max([self.regions[cr].max_branch_width(), self.regions[cr2].max_branch_width()]) * self.connection_threshold:
                            self.connected_crossroads.append((cr, cr2, (path, l)))

    # return a path (defined by a list of nodes) contained in the given link l that connects
    # the two given crossroad regions (cr1 and cr2)
    def get_path_in_link(self, l, cr1, cr2):
        cr1n = [n for n in self.regions[l].nodes if cr1 in self.regionsByNode[n]]
        cr2n = [n for n in self.regions[l].nodes if cr2 in self.regionsByNode[n]]

        return self.regions[l].get_path(cr1n, cr2n)

    def add_adjacencies(self, r1, node, regions):
        if not r1 in self.adjacencies:
            self.adjacencies[r1] = {}
        for r2 in regions:
            if r2 != r1 and self.get_typology(r1) != self.get_typology(r2):
                if not r2 in self.adjacencies[r1]:
                    self.adjacencies[r1][r2] = []
                self.adjacencies[r1][r2].append(node)

    def get_typology(self, rid):
        if rid in self.crossroads:
            return CrossroadConnections.typology_crossroad
        elif rid in self.links:
            return CrossroadConnections.typology_link
        else:
            return CrossroadConnections.typology_unknown
            

    def add_node_region(self, rid, nid):
        if not nid in self.regionsByNode:
            self.regionsByNode[nid] = []
        self.regionsByNode[nid].append(rid)

    def get_pairs(self):
        return [connected for connected in self.connected_crossroads if len(connected[2]) > 1]

    def get_cycles(self, max_length = 5):
        results = []

        for c in self.crossroads:
            results += self.get_cycles_from_crossroad(c, max_length)

        results = self.get_unique_cycles(results)

        return results

    def get_unique_cycles(self, cycles):
        result = []
        seen = []

        for c in cycles:
            celems = set([e[0] for e in c])
            if not celems in seen:
                result.append(c)
                seen.append(celems)

        return result

    def get_connected_crossroads(self, cr):
        result = []
        for connected in self.connected_crossroads:
            if connected[0] == cr:
                result.append((connected[1], connected[2]))
            elif connected[1] == cr:
                result.append((connected[0], connected[2]))
        return result

    def get_cycles_from_crossroad(self, cr, max_length):
        paths = [ [(cr, [])] ]
        results = []

        # increase step by step the possible paths
        for l in range(0, max_length):
            new_paths = []
            # for each existing path, compute all possible extensions (without backward)
            for p in paths:
                # check all possible next steps
                for next in self.get_connected_crossroads(p[-1][0]):
                    if len(p) == 1 or p[-2][0] != next[0] and not self.contains_link(next[1], p):
                        if next[0] == p[0][0]:
                            # loop detection
                            results.append(p + [next])
                        else:
                            # ongoing loop
                            new_paths.append(p + [next])
            paths = new_paths

        return results

    def contains_link(self, nextpathlinks, path):
        n_links = [c[1] for c in nextpathlinks]


        for p in path:
            for l in p[1]:
                if l[1] in n_links:
                    return True
        return False

