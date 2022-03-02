"""
Fichier Python crée par Diego (Jouca) concernant les fonctions du site
et l'affichage de celui-ci.
"""

from datetime import datetime
import base64
import hashlib
import re
import time
from flask import Flask, request, make_response, redirect, url_for
from flask import render_template, flash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_recaptcha import ReCaptcha
import mysql.connector as MC
import requests


# Connection à la base de données
DBHOST = "HOST"
DBDATABASE = "DATABASE"
DBUSER = "USER"
DBPASSWORD = "PASSWORD"

# Variable global
SECRET_CODE = "joucagame"

app = Flask(__name__)
# Code secret pour les cookies
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

# Codes secrets pour les capchats
app.config['RECAPTCHA_SITE_KEY'] = '6Ld5lRoeAAAAAOFbmoVPK2m2_qE5fKMssuZJa196'
app.config['RECAPTCHA_SECRET_KEY'] = '6Ld5lRoeAAAAAEMftxjGe1mbQ0bvRgOPQEM9yz7t'
recaptcha = ReCaptcha(app)
limiter = Limiter(app, key_func=get_remote_address)


def bddtest(host, database, user, password):
    """
    Permet de se connecter à la base de données.
    """
    try:
        conn = MC.connect(host=host,
                          database=database,
                          user=user,
                          password=password)
        cursor = conn.cursor(buffered=True)
    except MC.Error as err:
        print(err)
    return cursor, conn


def base64_decode(string: str) -> str:
    """
    Permet d'encoder une chaine de caractère en base64.
    """
    return base64.urlsafe_b64decode(string.encode()).decode()


def creation_compte(pseudo, motdepasse, ip_user, cursor, conn):
    """
    Permet de crée un compte sur le site avec un pseudo, un mot de passe et une IP.
    """
    motdepasse_crypt = hashlib.md5(motdepasse.encode()).hexdigest()
    now = datetime.now()
    formatted_date = now.strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute(
        """INSERT INTO utilisateurs
        (pseudo,motdepasse,adresse_IP,date_creation) VALUES (%s,%s,%s,%s)""",
        (pseudo, motdepasse_crypt, ip_user, formatted_date)
    )
    conn.commit()


def envoie_email(email, pseudo, message):
    """
    Permet d'envoyer un email à l'utilisateur.
    """
    data = requests.post(
        "https://clarifygdps.com/mastermind/controlleurs.php",
        data={"ml": email, "pr": pseudo, "ms": str(message)}
    )
    return data


def connexion_compte(pseudo, motdepasse, ip_user, cursor):
    """
    Permet de se connecter à un compte.
    """
    erreur = None

    if pseudo and motdepasse:
        if check_ip_ban(ip_user, cursor):
            cursor.execute(
                "SELECT motdepasse FROM utilisateurs WHERE pseudo = %s LIMIT 1",
                (pseudo,)
            )
            motdepasse_serveur = cursor.fetchone()
            if motdepasse_serveur:
                cursor.execute("""SELECT email_validated FROM utilisateurs
                    WHERE pseudo = %s LIMIT 1""", (pseudo,)
                               )
                email_validated = cursor.fetchone()
                if email_validated[0] == 1:
                    motdepasse = hashlib.md5(motdepasse.encode()).hexdigest()
                    if motdepasse_serveur[0] == motdepasse:
                        return "OK"
                    erreur = "Mot de passe incorrect."
                    return erreur
                erreur = "Email non validé."
                return erreur
            erreur = "Ce compte n'existe pas."
            return erreur
        erreur = """Votre IP est banni du serveur.
        Contacter par e-mail 'joucagame@gmail.com'"""
        return erreur
    return ""


def check_connexion_cookies():
    """
    Permet de vérifier si l'utilisateur est connecté via les cookies.
    """
    cursor, conn = bddtest(DBHOST, DBDATABASE, DBUSER, DBPASSWORD)
    pseudo = request.cookies.get('Pseudo')
    motdepasse = request.cookies.get('Motdepasse')
    addresse_ip = request.remote_addr
    if pseudo and motdepasse:
        if connexion_compte(pseudo, motdepasse, addresse_ip, cursor) == "OK":
            return pseudo
    return None


def deconnexion_cookies():
    """
    Permet de déconnecter l'utilisateur via les cookies.
    """
    resp = make_response(redirect(url_for("connexion")))
    resp.set_cookie('Pseudo', "", expires=0)
    resp.set_cookie("Motdepasse", "", expires=0)
    return resp


def check_ip_ban(ip_user, cursor):
    """
    Permet de vérifier si l'utilisateur est banni via IP.
    """
    cursor.execute("SELECT IP FROM ip_bannis WHERE IP = %s", (ip_user,))
    adresse_ip_banni = cursor.fetchone()
    if adresse_ip_banni is None:
        return True
    return False


def check_role(pseudo, cursor):
    """
    Permet de vérifier le rôle de l'utilisateur.
    """
    cursor.execute(
        "SELECT role FROM utilisateurs WHERE pseudo = %s",
        (pseudo,)
    )
    role_id = cursor.fetchone()
    if role_id[0] != 0:
        cursor.execute(
            "SELECT nom FROM roles WHERE roleID = %s",
            (role_id[0],)
        )
        nomrole = cursor.fetchone()
        if nomrole:
            return nomrole[0]
    return None


def get_leaderboard_stats(method):
    """
    Permet de récupérer les statistiques du classement.
    """
    liste = []
    cursor, conn = bddtest(DBHOST, DBDATABASE, DBUSER, DBPASSWORD)
    cursor.execute(
        """SELECT pseudo,score FROM score,utilisateurs WHERE
        utilisateurs.ID = score.userID ORDER BY score DESC"""
    )
    scores = cursor.fetchall()
    for values in enumerate(scores):
        liste.append([values[0] + 1, values[1][0], values[1][1]])
    if method == "GET":
        return liste
    texte = ""
    for values in liste:
        texte += str(values[0]) + "#" + str(values[1]) + "#" + str(values[2]) + ":"
    conn.close()
    return texte


@app.route("/connexion/", methods=["GET", "POST"])
@limiter.limit("10/minute")
def connexion():
    """
    Endpoint pour tester les informations de connexion de l'utilisateur
    """
    if request.method == "GET":
        if check_connexion_cookies() is not None:
            return redirect(url_for("account"))
        return render_template("connexion.html")
    cursor, conn = bddtest(DBHOST, DBDATABASE, DBUSER, DBPASSWORD)
    jsondata = request.get_json()
    if jsondata:
        pseudo = jsondata["pseudo"]
        motdepasse = jsondata["motdepasse"]
        adresse_ip = request.remote_addr
        check = connexion_compte(pseudo, motdepasse, adresse_ip, cursor)
        if check == "OK":
            return "OK"
    return "-1"


@app.route("/deconnexion/", methods=["GET", "POST"])
@limiter.limit("10/minute")
def deconnexion():
    """
    Endpoint pour déconnecter l'utilisateur.
    """
    return deconnexion_cookies()


@app.route("/account/", methods=["GET", "POST"])
@limiter.limit("10/minute")
def account():
    """Endpoint pour tester les informations de connexion de l'utilisateur"""
    if request.method == "GET":
        check_compte = check_connexion_cookies()
        if check_compte is not None:
            cursor, conn = bddtest(DBHOST, DBDATABASE, DBUSER, DBPASSWORD)
            nomrole = check_role(check_compte, cursor)
            return render_template(
                "account.html",
                pseudo=check_compte,
                role=nomrole
            )
        return redirect(url_for("connexion"))
    cursor, conn = bddtest(DBHOST, DBDATABASE, DBUSER, DBPASSWORD)

    pseudo = request.form.get('pseudo')
    motdepasse = request.form.get('motdepasse')
    adresse_ip = request.remote_addr
    if recaptcha.verify():
        result = connexion_compte(pseudo, motdepasse, adresse_ip, cursor)
        if result == "OK":
            now = datetime.now()
            unixtime = time.mktime(now.timetuple()) + 3600
            nomrole = check_role(pseudo, cursor)
            resp = make_response(
                render_template(
                    "account.html",
                    pseudo=pseudo,
                    role=nomrole
                )
            )
            resp.set_cookie('Pseudo', pseudo, expires=unixtime)
            resp.set_cookie("Motdepasse", motdepasse, expires=unixtime)
            return resp
        flash(result)
        return redirect(url_for("connexion"))
    flash("Captcha invalide")
    return redirect(url_for("connexion"))


@app.route("/account/change_motdepasse/", methods=["POST", "GET"])
@limiter.limit("10/minute")
def change_motdepasse():
    """
    Endpoint pour changer le mot de passe de l'utilisateur.
    """
    if request.method == "GET":
        check_compte = check_connexion_cookies()
        if check_compte is not None:
            return render_template("change_motdepasse.html")
        return deconnexion_cookies()
    cursor, conn = bddtest(DBHOST, DBDATABASE, DBUSER, DBPASSWORD)
    erreur = None
    success = None

    motdepasse = hashlib.md5(
        request.form.get('motdepasse').encode()
    ).hexdigest()
    newmotdepasse = hashlib.md5(
        request.form.get('newmotdepasse').encode()
    ).hexdigest()
    pseudo = request.cookies.get('Pseudo')
    adresse_ip = request.remote_addr
    if motdepasse and newmotdepasse and pseudo:
        if check_ip_ban(adresse_ip, cursor):
            cursor.execute(
                """SELECT pseudo,motdepasse FROM utilisateurs
                WHERE pseudo = %s""",
                (pseudo,)
            )
            pseudo_serveur = cursor.fetchone()
            if pseudo_serveur is not None:
                pseudo = pseudo_serveur[0]
                motdepasse_serveur = pseudo_serveur[1]
                if motdepasse_serveur == motdepasse:
                    cursor.execute(
                        """UPDATE utilisateurs SET motdepasse = %s
                        WHERE pseudo = %s""",
                        (newmotdepasse, pseudo_serveur[0],)
                    )
                    conn.commit()
                    success = "Mot de passe changé !"
                    now = datetime.now()
                    unixtime = time.mktime(now.timetuple()) + 3600
                    resp = make_response(
                        redirect(
                            url_for("change_motdepasse")
                        )
                    )
                    resp.set_cookie('Pseudo', pseudo, expires=unixtime)
                    resp.set_cookie(
                        "Motdepasse",
                        newmotdepasse,
                        expires=unixtime
                    )
                    flash(success)
                    return resp
                erreur = "Mot de passe incorrect"
            else:
                return deconnexion_cookies()
        else:
            return deconnexion_cookies()
    if erreur:
        flash(erreur)
    return redirect(url_for("change_motdepasse", success=success))


@app.route("/leaderboard/request", methods=["POST"])
@limiter.limit("100/minute")
def request_leaderboard():
    """
    Endpoint pour envoyer un score sur le classement.
    """
    jsondata = request.form
    if not jsondata:
        return "-1"
    cursor, conn = bddtest(DBHOST, DBDATABASE, DBUSER, DBPASSWORD)
    pseudo = jsondata["pseudo"]
    motdepasse = jsondata["motdepasse"]
    score = jsondata["score"]
    secret = jsondata["secret"]
    if pseudo and motdepasse and score and secret:
        adresse_ip = request.remote_addr
        check = connexion_compte(pseudo, motdepasse, adresse_ip, cursor)
        if check == "OK":
            if secret == SECRET_CODE:
                cursor.execute(
                    """SELECT score FROM score WHERE userID =
                    (SELECT ID FROM utilisateurs WHERE pseudo = %s)""",
                    (pseudo,)
                )
                data = cursor.fetchone()
                if data is not None:
                    if int(score) > int(data[0]):
                        cursor.execute(
                            """UPDATE score SET score = %s WHERE userID =
                            (SELECT ID FROM utilisateurs WHERE
                            pseudo = %s)""",
                            (score, pseudo,)
                        )
                        conn.commit()
                        return "OK"
                    return "Score trop faible."
                cursor.execute(
                    """INSERT INTO score(userID, score) VALUES
                    ((SELECT ID FROM utilisateurs WHERE pseudo = %s),
                    %s)""",
                    (pseudo, score,)
                )
                conn.commit()
                return "OK"
    return "-1"


@app.route("/leaderboard/", methods=["GET", "POST"])
@limiter.limit("10/minute")
def leaderboard():
    """
    Endpoint pour afficher le classement.
    """
    if request.method == "GET":
        return render_template(
            "leaderboard.html",
            test=get_leaderboard_stats("GET")
        )
    return str(get_leaderboard_stats("POST"))


@app.route("/inscription/")
@limiter.limit("10/minute")
def inscription():
    """
    Endpoint pour afficher la page d'inscription.
    """
    return render_template("inscription.html")


@app.route("/email_verification", methods=["GET"])
@limiter.limit("1/minute")
def email_verification():
    """
    Endpoint pour vérifier l'adresse email.
    """
    cursor, conn = bddtest(DBHOST, DBDATABASE, DBUSER, DBPASSWORD)
    id_user = request.args.get("id")
    pseudo = request.args.get("pseudo")
    if id_user and pseudo:
        cursor.execute(
            "SELECT code,email FROM email_verification WHERE code = %s LIMIT 1",
            (id_user,)
        )
        idverified = cursor.fetchone()
        if idverified:
            cursor.execute(
                """UPDATE utilisateurs SET email_validated = 1, email = %s
                WHERE pseudo = %s""",
                (idverified[1], pseudo,)
            )
            cursor.execute(
                "DELETE FROM email_verification WHERE code = %s",
                (id_user,)
            )
            conn.commit()
            flash("OK_EMAIL")
    return redirect(url_for("connexion"))


@app.route("/inscription/resultat/", methods=["POST", "GET"])
@limiter.limit("5/minute")
def resultat():
    """
    Endpoint pour afficher le résultat de l'inscription.
    """
    if request.method == "GET":
        return redirect(url_for("inscription"))
    cursor, conn = bddtest(DBHOST, DBDATABASE, DBUSER, DBPASSWORD)
    erreur = None

    pseudo = request.form.get('pseudo')
    email = request.form.get('email')
    motdepasse = request.form.get('motdepasse')
    motdepasse_repeat = request.form.get('repeatmotdepasse')
    adresse_ip = request.remote_addr
    if check_ip_ban(adresse_ip, cursor):
        erreur = """Votre IP est banni du serveur.
                Contacter par e-mail 'joucagame@gmail.com'"""
    if pseudo and email and motdepasse and motdepasse_repeat:
        if recaptcha.verify():
            cursor.execute(
                """SELECT pseudo FROM utilisateurs
                WHERE pseudo = %s""",
                (pseudo,)
            )
            pseudo_serveur = cursor.fetchone()
            if pseudo_serveur is None:
                pattern = re.compile("[A-Za-z0-9]+")
                if pattern.fullmatch(pseudo) is not None:
                    if motdepasse == motdepasse_repeat:
                        creation_compte(
                            pseudo,
                            motdepasse,
                            adresse_ip,
                            cursor,
                            conn
                        )
                        random_code = hashlib.md5(
                            email.encode()
                        ).hexdigest()
                        cursor.execute(
                            """INSERT INTO email_verification
                            (email,code,pseudo) VALUES (%s, %s, %s)""",
                            (email, random_code, pseudo)
                        )
                        conn.commit()
                        url = "http://tetrisnsi.tk/"
                        html = f"{url}email_verification?id={random_code}&pseudo={pseudo}"
                        envoie_email(email, pseudo, f'''<h1>Bonjour
                            <b>{pseudo}</b></h1><br><br><p>Nous avons bien
                            reçu votre demande de création de compte.
                            <br>Afin de vérifier que votre compte est
                            bien lié avec votre addresse email, vous
                            devez cliquer sur le lien situé en
                            dessous de ce texte pour pouvoir
                            vérifier votre compte.</p><br><br>
                            <a href='{html}'>Cliquer ici pour
                            vérifier votre compte</a>'''
                                     )
                        flash(pseudo)
                        return render_template("success.html")
                    erreur = """Les mots de passes ne
                        correspondent pas."""
                else:
                    erreur = """Votre pseudonyme comporte des
                        caractères spéciaux.\nNous n'acceptons que les
                        chiffres et les lettres sur vôtre pseudonyme."""
            else:
                erreur = "Pseudonyme déjà pris."
        else:
            erreur = "Captcha non vérifié."
    flash(erreur)
    return redirect(url_for("inscription"))


@app.route("/")
def index():
    """
    Endpoint pour afficher la page d'accueil.
    """
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1501)
