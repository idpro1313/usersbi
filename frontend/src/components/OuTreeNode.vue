<script>
export default {
  name: 'OuTreeNode',
  props: {
    node: Object,
    parentPath: String,
    domainKey: String,
    filter: { type: String, default: '' },
    selectedPath: String,
    selectedDomain: String,
  },
  emits: ['select'],
  computed: {
    nodePath() {
      return this.parentPath ? this.parentPath + '/' + this.node.name : this.node.name
    },
    hasChildren() { return this.node.children && this.node.children.length > 0 },
    isActive() { return this.nodePath === this.selectedPath && this.domainKey === this.selectedDomain },
    nameMatch() { return !this.filter || this.node.name.toLowerCase().includes(this.filter) },
    childrenMatch() { return this.hasMatchInChildren(this.node.children, this.filter) },
    visible() { return !this.filter || this.nameMatch || this.childrenMatch },
  },
  data() {
    return { expanded: !!this.filter }
  },
  watch: {
    filter(val) { if (val && this.childrenMatch) this.expanded = true }
  },
  methods: {
    hasMatchInChildren(children, filter) {
      if (!filter || !children) return false
      for (const c of children) {
        if (c.name.toLowerCase().includes(filter)) return true
        if (this.hasMatchInChildren(c.children, filter)) return true
      }
      return false
    },
    toggle() { this.expanded = !this.expanded },
    select() { this.$emit('select', this.nodePath, this.domainKey) },
    onChildSelect(p, d) { this.$emit('select', p, d) },
  },
}
</script>

<template>
  <div v-if="visible" class="tree-ou-node">
    <div class="tree-ou-row">
      <span v-if="hasChildren" class="tree-arrow" @click.stop="toggle"
        v-html="expanded ? '&#9660;' : '&#9654;'"></span>
      <span v-else class="tree-arrow-spacer"></span>
      <span class="tree-ou-item" :class="{ active: isActive }" @click="select">
        {{ node.name }} <span class="tree-group-count">({{ node.count }}/{{ node.total }})</span>
      </span>
    </div>
    <div v-if="hasChildren && expanded" class="tree-ou-children">
      <OuTreeNode v-for="child in node.children" :key="child.name"
        :node="child" :parentPath="nodePath" :domainKey="domainKey"
        :filter="filter" :selectedPath="selectedPath" :selectedDomain="selectedDomain"
        @select="onChildSelect" />
    </div>
  </div>
</template>
