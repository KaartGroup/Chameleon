import "./App.css";
import {
    BrowserRouter as Router,
    Switch,
    Route,
    Redirect,
} from "react-router-dom";

import { Header } from "./components/Header";
import { Footer } from "./components/Footer";
import { PageNotFound } from "./components/PageNotFound";
import { Chameleon } from "./components/Chameleon";
import { ChameleonProvider } from "./common/ChameleonContext";
import { BYOD } from "./components/BYOD";

function App() {
    return (
        <Router>
            <ChameleonProvider>
                <Header />
                <Switch>
                    <Route exact={true} path="/">
                        <Redirect to="/chameleon" />
                    </Route>
                    <Route path="/chameleon">
                        <Chameleon />
                    </Route>
                    <Route path="/byod">
                        <BYOD />
                    </Route>
                    <Route component={PageNotFound} />
                </Switch>
                <Footer />
            </ChameleonProvider>
        </Router>
    );
}

export default App;
