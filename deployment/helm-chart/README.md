**Structure of the CNAP helm-chart**
  Chart.yaml          # A YAML file containing information about the chart
  LICENSE             # OPTIONAL: A plain text file containing the license for the CNAP chart
  README.md           # OPTIONAL: A human-readable README file
  values.yaml         # The default configuration values for the CNAP chart
  values.schema.json  # OPTIONAL: A JSON Schema for imposing a structure on the values.yaml file
  charts/             # A directory containing any charts upon which the CNAP chart depends
  crds/               # Custom Resource Definitions
  templates/          # A directory of templates that, when combined with values,
                      # will generate valid Kubernetes manifest files
  templates/NOTES.txt # OPTIONAL: A plain text file containing short usage notes

*Note* - Helm reserves use of the charts/, crds/, and templates/ directories, and of the above listed file names. Other files will be left as they are.

