export default {
  title: "dismech ↔ HPOA",
  root: "src",
  theme: ["air", "near-midnight"],
  pages: [
    {name: "Overview", path: "/"},
    {name: "Disease coverage", path: "/coverage"},
    {name: "Per-disease", path: "/diseases"},
    {name: "Novel & missing", path: "/diff"},
    {name: "Methods", path: "/methods"},
  ],
  header: "dismech ↔ HPOA — hierarchy-aware phenotype comparison",
  footer:
    'Compares dismech\'s <code>phenotype.dismech.hpoa</code> export against HPO\'s ' +
    '<code>phenotype.hpoa</code>, reconciled via MONDO SSSOM.',
  toc: true,
};
