from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps
#Makale formu
def addarticle():
    title = StringField("Başlık")
    content = TextAreaField("Makale içeriği",validators=[validators.Length(min=5)])
#Kullanıcı giriş decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı bu şekilde göremezsin.","danger")
            return redirect(url_for("giris"))
    return decorated_function
#kullanıcı giriş formu
class RegisterForm(Form):
    name = StringField("İsim Soyisim",validators=[validators.Length(min=4,max=25)])
    username = StringField("Kullanıcı Adı",validators=[validators.Length(min=5,max=35)])
    email = StringField("Email Adresi",validators=[validators.Email(message="Lütfen geçerli bir mail adresi girin.")])
    password = PasswordField("Parola",validators=[
        validators.DataRequired(message="Lütfen bir parola belirleyin."),
        validators.EqualTo(fieldname= "confirm",message="Parolanız uyuşmuyor.") # confirm ile eşleyeccek eğer uyuşmazsa hata
        ])
    confirm = PasswordField("Parola doğrula")
#Login formu
class LoginForm(Form):
    username = StringField("Kullanıcı Adı",validators=[validators.DataRequired(message="Lütfen bu alanı boş bırakmayınız.")])
    password = PasswordField("Parola",validators=[validators.DataRequired(message="Lütfen bu alanı boş bırakmayınız."),
    validators.EqualTo(fieldname="confirm",message="Paralolar uyuşmuyor.")])
    confirm = PasswordField("Parola doğrula")
app=Flask(__name__)
app.secret_key = "mustafa"
#flask mysql connection
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "guestsdb"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)
# form mantığı = class oluşturularak
@app.route("/")
def index():
    numbers = [1,2,3,4,5]
    return render_template("index.html", numberlar = numbers)
@app.route("/hakkimizda")
def about():
    return render_template("about.html")
@app.route("/kayitol",methods = ["GET","POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)
        cursor = mysql.connection.cursor()
        sorgu = "Insert into users(name,username,email,password) VALUES (%s,%s,%s,%s)"
        cursor.execute(sorgu,(name,username,email,password))
        mysql.connection.commit()
        cursor.close()
        flash("Başarıyla kayıt oldunuz.","success")
        return redirect(url_for("giris"))
    else:
        return render_template("register.html",form=form)
@app.route("/login",methods = ["GET","POST"])
#Giriş yap
def giris():
    form=LoginForm(request.form)
    if request.method == "POST" and form.validate():
        username = form.username.data
        password_entered = form.password.data
        cursor = mysql.connection.cursor()
        sorgu = "Select * from users where username= %s"
        username_result = cursor.execute(sorgu,(username,))
        if username_result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password_entered,real_password):
                session["logged_in"] = True
                session["username"] = username
                flash("Başarıyla giriş yaptınız.","success")
                return redirect(url_for("index"))
                
            else:
                flash("Parola yanlış girilmiştir.","danger")
                return redirect(url_for("giris"))
        else:
            flash("Böyle bir kullanıcı bulunmuyor.","danger")
            return redirect(url_for("giris"))
             
    else:
        return render_template("login.html",form=form)
#Kontrol Paneli
@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    sorgu = "Select * from articles where author=%s"
    result = cursor.execute(sorgu,(session["username"],))
    if result >0:
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles=articles)
    else:
        return render_template("dashboard.html")
#Makale oluşturma
@app.route("/addarticle",methods=["GET","POST"])
def addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data
        cursor = mysql.connection.cursor()
        sorgu = "Insert into articles(title,author,content) VALUES (%s,%s,%s)"
        cursor.execute(sorgu,(title,session["username"],content))
        mysql.connection.commit()
        cursor.close()
        flash("Makale başarıyla eklendi.","success")
        return redirect(url_for("dashboard"))
    return render_template("addarticle.html",form=form)
# Makale Formu
class ArticleForm(Form):
    title = StringField("Makale Başlığı: ",validators=[validators.Length(min=5,max=100)])
    content = TextAreaField("Makale İçeriği: ",validators=[validators.Length(min=10)])
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    sorgu = "Select * from articles"
    result = cursor.execute(sorgu)
    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html",articles = articles)
    else:
        return render_template("articles.html")
#Delete article
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu ="Select * from articles where author=%s and id=%s"
    result = cursor.execute(sorgu,(session["username"],id))
    if result > 0:
        sorgu2="Delete from articles where id=%s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()
        flash("Makale başarı ile silindi.","warning")
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok.","warning")
        return redirect(url_for("index"))
#edit article
@app.route("/edit/<string:id>",methods={"GET","POST"})
@login_required
def edit(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        sorgu ="Select * from articles where id=%s"
        result = cursor.execute(sorgu,(id,))
        if result ==0 :
            flash("Böyle bir makale yok. Editleyemezsin.","warning")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html",form= form)
    else:
        #post request
        form = ArticleForm(request.form)
        newtitle = form.title.data
        newcontent = form.content.data
        sorgu2 = "Update articles set title= %s,content=%s where id=%s"
        cursor = mysql.connection.cursor()
        cursor.execute(sorgu2,(newtitle,newcontent,id))
        mysql.connection.commit()
        flash("Makale güncellendi.","warning")
#Çıkış
@app.route("/logout")
def cikis():
    session.clear()
    return redirect(url_for("index"))
@app.route("/articles/<string:id>")
def detail(id):
    cursor = mysql.connection.cursor()
    sorgu = "Select * from articles where id=%s"
    result = cursor.execute(sorgu,(id,))
    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html",article=article)
    else:
        return render_template("article.html")
if __name__ == "__main__":
    app.run(debug=True)