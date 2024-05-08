# volume_gizmos
Browser based interactive 3d data array visualizations

This project is currently an Alpha in development.

# Development (or experimental) install

To install an experimental version of volume_gizmos, first clone or download
the Github repository and then install in developer mode as follows:

```bash
 cd volume_gizmos
 pip install -e .
```

## Update javascript dependencies

NPM is used to manage Javascript packages and dependencies.
The Javascript is frozen in the Python package.
To load the latest Javascript, use the following command:

```bash
rm -rf package-lock.json node_modules volume_gizmos/node_modules
npm install
cp -r node_modules volume_gizmos/
```

Then commit the updates to the git repository.
