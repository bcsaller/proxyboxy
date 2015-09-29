var ProxyBoxy = React.createClass({
    getInitialState: function() {
        return {
            selected: null,
            data: []
        };
    },

    loadEndpoints: function() {
        $.getJSON("/endpoints/", function(endpoints) {
            this.setState({data: endpoints});
        }.bind(this));
    },

    handleSelect: function(entity) {
        this.state.data.map(function(e) {
            var node = this.refs[e.name];
            node.setState({selected: false});
        }.bind(this));
        this.refs[entity.name].setState({selected: true});
        this.editor.setValue(entity);
        $('#editor_holder').focus();
    },

    handleDelete: function(entity, evt) {
        evt.preventDefault();
        var data = [];
        this.state.data.map(function(e) {
            if (entity.name !== e.name) {
                data.push(e);
            }
        });
        var message = $("#editor_status");
        $.ajax({type: "DELETE",
               url: "/endpoint/",
               data: JSON.stringify(entity),
               processData: false,
               complete: function(xhr, status) {
                   if (status === "error") {
                       message.text(xhr.responseText);
                   } else {
                       message.text("Saved");
                       window.location = "/";
                   }
               }
        });
        this.setState({data: data});
    },

    componentDidMount: function() {
        $.getJSON("/schema/").then(function(schema) {
            var editor = new JSONEditor(document.getElementById("editor_holder"),{
            schema: schema,
            no_additional_properties: false,
            disable_collapse: true,
            disable_edit_json: true,
            disable_properties: false
            });
            this.editor = editor;
            var save = $("#editor_save");
            var message = $("#editor_status");

            save.on("click", function(e) {
                var errors = editor.validate();
                if (!errors.length) {
                    var data = editor.getValue();
                    $.ajax({
                        type: "POST",
                        url: "/endpoint/",
                        data: JSON.stringify(data),
                        processData: false,
                        complete: function(xhr, status) {
                            if (status === "error") {
                                message.text(xhr.responseText);
                            } else {
                                message.text("Saved");
                                window.location = "/";
                            }
                        }
                    })} else {
                        message.text(errors);
                    };
            });
        }.bind(this))
        .then(this.loadEndpoints);
    },

    render: function() {
        var endpoints = this.state.data.map(function(entity, index) {
            return (
                <Endpoint onClick={this.handleSelect.bind(null, entity)}
                          delete={this.handleDelete.bind(null, entity)}
                          key={entity.name}
                          name={entity.name}
                          ref={entity.name}
                          interface={entity.interface}
                          data={entity.data}/>
            );
        }.bind(this));

        return (
            <div>
                <pre id="editor_status"></pre>
                <div className="endpointBox">
                    <div className="endpoints">
                        {endpoints}
                    </div>
                </div>
                <div id="editor_holder"></div>
                <input id="editor_save" type="button" className="pure-button" value="submit"></input>
            </div>
        );
    }
});

var Endpoint = React.createClass({
    render: function() {
        var selected = "";
        if (this.state && this.state.selected === true) {
            selected="selected";
        }
        return (
            <div onClick={this.props.onClick} className="endpoint">
                <div className={selected}>
                    <div className="name">{this.props.name}</div>
                    <div className="interface">{this.props.interface}</div>
                    <div className="data">{JSON.stringify(this.props.data, undefined, 2)}</div>
                    <div className="control">
                        <button onClick={this.props.delete} name="delete">X</button>
                    </div>
                </div>
            </div>
        );
    }
});


