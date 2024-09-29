<%@ Page Language="C#" AutoEventWireup="true" %>
<%@ Import Namespace="System.IO" %>
<%@ Import Namespace="System.Net" %>
<%@ Import Namespace="System.Security.Authentication" %>

<script runat="server">
    void Page_Load(object sender, EventArgs e)
    {
        ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12 | SecurityProtocolType.Tls13;

        string videoId = Request.QueryString["url"];

        if (string.IsNullOrEmpty(videoId))
        {
            Response.Write("No video ID provided.");
            return;
        }

        try
        {
            string mp3Url = GetMp3DownloadUrl(videoId);

            if (string.IsNullOrEmpty(mp3Url))
            {
                Response.Write("Failed to get MP3 URL.");
                return;
            }

            StreamMp3ToUser(mp3Url);
        }
        catch (Exception ex)
        {
            Response.Write("Error during conversion: " + ex.Message);
        }
    }

    string GetMp3DownloadUrl(string videoId)
    {
        string videoUrl = "https://www.youtube.com/watch?v=" + videoId;
        string postData = "{\"url\":\"" + videoUrl + "\",\"isAudioOnly\":true,\"filenamePattern\":\"pretty\"}";

        HttpWebRequest request = (HttpWebRequest)WebRequest.Create("https://cnvmp3.com/fetch.php");
        request.Method = "POST";
        request.ContentType = "application/json";
        request.UserAgent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36";

        using (var streamWriter = new StreamWriter(request.GetRequestStream()))
        {
            streamWriter.Write(postData);
        }

        using (var response = (HttpWebResponse)request.GetResponse())
        {
            using (var reader = new StreamReader(response.GetResponseStream()))
            {
                string result = reader.ReadToEnd();
                return ExtractMp3Url(result);
            }
        }
    }

    string ExtractMp3Url(string jsonResponse)
    {
        int urlIndex = jsonResponse.IndexOf("\"url\":\"") + 7;
        int urlEnd = jsonResponse.IndexOf("\"", urlIndex);
        return jsonResponse.Substring(urlIndex, urlEnd - urlIndex);
    }

    void StreamMp3ToUser(string mp3Url)
    {
        HttpWebRequest request = (HttpWebRequest)WebRequest.Create(mp3Url);
        request.Method = "GET";

        using (var response = (HttpWebResponse)request.GetResponse())
        {
            using (var stream = response.GetResponseStream())
            {
                Response.ContentType = "audio/mpeg";
                Response.AddHeader("Content-Disposition", "inline; filename=\"audio.mp3\"");
                Response.AddHeader("Accept-Ranges", "bytes"); 
                stream.CopyTo(Response.OutputStream);
            }
        }
    }
</script>
